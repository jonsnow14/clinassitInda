from __future__ import annotations

from ..models import RetrievedChunk
from .ingest import chroma_ready, collection

SCORE_FLOOR_DISTANCE = 1.35  # chroma default L2 on MiniLM; lower is closer


def retrieve(query: str, k: int = 6) -> list[RetrievedChunk]:
    if not chroma_ready():
        raise RuntimeError("ICMR Chroma index is empty. Run: python -m app.rag.ingest")
    col = collection(create=False)
    res = col.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    chunks: list[RetrievedChunk] = []
    for doc, meta, dist in zip(docs, metas, dists):
        if dist is not None and dist > SCORE_FLOOR_DISTANCE:
            continue
        meta = meta or {}
        chunks.append(
            RetrievedChunk(
                text=doc or "",
                stw_title=str(meta.get("stw_title") or "ICMR STW"),
                section=str(meta.get("section") or ""),
                pdf=str(meta.get("pdf") or ""),
                page=meta.get("page"),
                score=None if dist is None else round(1.0 / (1.0 + float(dist)), 3),
            )
        )
    return chunks
