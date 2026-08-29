from __future__ import annotations

import re
import sys
from pathlib import Path

import httpx
from pypdf import PdfReader

from ..paths import CHROMA_DIR, ICMR_PDF_DIR

COLLECTION = "icmr_stws"

# Smaller condition PDFs first. cardiology_all is large and optional if it flakes.
ICMR_PDFS: list[tuple[str, str, str, bool]] = [
    (
        "nstemi.pdf",
        "https://www.icmr.gov.in/icmrobject/uploads/STWs/1768823342_cardiology_1-4.pdf",
        "ICMR STW Unstable Angina / NSTEMI",
        True,
    ),
    (
        "endocrinology.pdf",
        "https://www.icmr.gov.in/icmrobject/uploads/STWs/1733214641_endocrinology.pdf",
        "ICMR STW Endocrinology (Diabetes Type 1/2, DKA)",
        True,
    ),
    (
        "stemi_npncd_2022.pdf",
        "https://www.nhmmizoram.org/upload/Fin%20-%20STEMI%20Guidline-1.pdf",
        "MoHFW NP-NCD STEMI Guidelines 2022 (PHC/CHC reperfusion; cites ICMR STW)",
        False,
    ),
    (
        "cardiology_all.pdf",
        "https://www.icmr.gov.in/icmrobject/uploads/STWs/1771492083_cardiology_all.pdf",
        "ICMR STW Cardiology (NSTEMI, STEMI, Heart Failure, Angina, AF)",
        False,
    ),
]

HEADING_RE = re.compile(r"^(?:standard treatment workflow|stw|unstable angina|nstemi|stemi|heart failure|diabetes|hypertension|atrial|stable angina)", re.I)


def _looks_pdf(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 1000:
        return False
    with path.open("rb") as fh:
        return fh.read(5).startswith(b"%PDF")


def _download_one(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    headers = {"User-Agent": "ClinAssistIndia/1.0 (ICMR STW ingest; research POC)"}
    last_err: Exception | None = None
    for attempt in range(1, 4):
        try:
            with httpx.Client(timeout=120.0, follow_redirects=True, headers=headers) as client:
                with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    with tmp.open("wb") as fh:
                        for chunk in resp.iter_bytes(1024 * 64):
                            fh.write(chunk)
            if not _looks_pdf(tmp):
                raise RuntimeError(f"not a PDF ({tmp.stat().st_size} bytes)")
            tmp.replace(dest)
            return
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"  attempt {attempt} failed: {exc}")
            if tmp.exists():
                tmp.unlink()
    raise RuntimeError(f"download failed after retries: {url} ({last_err})") from last_err


def download_pdfs(force: bool = False) -> list[Path]:
    ICMR_PDF_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for filename, url, _title, required in ICMR_PDFS:
        dest = ICMR_PDF_DIR / filename
        if _looks_pdf(dest) and not force:
            saved.append(dest)
            print(f"cached {dest.name} ({dest.stat().st_size} bytes)")
            continue
        print(f"downloading {url}")
        try:
            _download_one(url, dest)
            print(f"wrote {dest} ({dest.stat().st_size} bytes)")
            saved.append(dest)
        except Exception as exc:
            if required:
                raise RuntimeError(
                    f"Failed to download required ICMR PDF {filename} from {url}: {exc}"
                ) from exc
            print(f"WARNING: optional PDF skipped ({filename}): {exc}")
    if not saved:
        raise RuntimeError("No ICMR PDFs downloaded")
    return saved


def _pages(path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(path))
    out: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) < 80:
            continue
        out.append((i, text))
    return out


def _chunks(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    if len(text) <= size:
        return [text]
    parts: list[str] = []
    i = 0
    while i < len(text):
        parts.append(text[i : i + size].strip())
        i += size - overlap
    return [p for p in parts if len(p) > 60]


def _title_for(filename: str, chunk: str, default: str) -> str:
    for line in chunk.splitlines()[:8]:
        clean = line.strip(" -:\t")
        if HEADING_RE.search(clean) and 8 < len(clean) < 80:
            return clean
    mapping = {item[0]: item[2] for item in ICMR_PDFS}
    return mapping.get(filename, default)


def embedding_function():
    try:
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        return ONNXMiniLM_L6_V2()
    except Exception:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        return DefaultEmbeddingFunction()


def collection(create: bool = True):
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    kwargs = {"name": COLLECTION, "embedding_function": embedding_function()}
    if create:
        return client.get_or_create_collection(**kwargs)
    return client.get_collection(**kwargs)


def chroma_ready() -> bool:
    if not CHROMA_DIR.exists():
        return False
    try:
        col = collection(create=False)
        return col.count() > 0
    except Exception:
        return False


def ingest(force: bool = False) -> int:
    if chroma_ready() and not force:
        col = collection(create=False)
        print(f"chroma already has {col.count()} chunks")
        return col.count()

    download_pdfs(force=force)
    pdfs = sorted(ICMR_PDF_DIR.glob("*.pdf"))
    records: list[dict] = []
    for path in pdfs:
        pages = _pages(path)
        print(f"{path.name}: {len(pages)} text pages")
        if not pages:
            print(f"WARNING: {path.name} yielded almost no text (infographic PDF?)")
            continue
        default_title = next((t for n, _u, t, _req in ICMR_PDFS if n == path.name), path.stem)
        idx = 0
        for page_no, page_text in pages:
            for chunk in _chunks(page_text):
                title = _title_for(path.name, chunk, default_title)
                records.append(
                    {
                        "id": f"{path.stem}-p{page_no}-{idx}",
                        "document": f"STW: {title} | page {page_no}\n{chunk}",
                        "metadata": {
                            "pdf": path.name,
                            "stw_title": title,
                            "section": f"page {page_no}",
                            "page": page_no,
                        },
                    }
                )
                idx += 1
    if not records:
        raise RuntimeError("No extractable ICMR text — refusing to create an empty index")

    import chromadb

    if CHROMA_DIR.exists() and force:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass

    col = collection(create=True)
    batch = 64
    for i in range(0, len(records), batch):
        sl = records[i : i + batch]
        col.upsert(
            ids=[r["id"] for r in sl],
            documents=[r["document"] for r in sl],
            metadatas=[r["metadata"] for r in sl],
        )
        print(f"upserted {min(i + batch, len(records))}/{len(records)}")
    print(f"index ready: {col.count()} chunks")
    return col.count()


def smoke() -> None:
    queries = [
        "unstable angina NSTEMI PHC aspirin clopidogrel heparin",
        "STEMI thrombolysis PHC ECG",
        "type 2 diabetes metformin",
    ]
    col = collection(create=False)
    for q in queries:
        print(f"\n=== {q} ===")
        res = col.query(query_texts=[q], n_results=3, include=["documents", "metadatas", "distances"])
        docs = res.get("documents") or [[]]
        metas = res.get("metadatas") or [[]]
        dists = res.get("distances") or [[]]
        for doc, meta, dist in zip(docs[0], metas[0], dists[0]):
            print(f"  [{dist:.3f}] {meta.get('stw_title')} ({meta.get('pdf')})")
            print("   ", (doc or "").replace("\n", " ")[:220])


def main() -> None:
    from ..paths import load_dotenv

    load_dotenv()
    force = "--force" in sys.argv or bool(__import__("os").getenv("INGEST_FORCE"))
    ingest(force=force)
    smoke()


if __name__ == "__main__":
    main()
