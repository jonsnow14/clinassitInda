from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
API_DIR = APP_DIR.parent
REPO_ROOT = API_DIR.parent.parent
DATA_DIR = REPO_ROOT / "data"
PURNIA_DIR = DATA_DIR / "purnia"
ICMR_PDF_DIR = DATA_DIR / "icmr" / "pdfs"
CHROMA_DIR = DATA_DIR / "chroma"
FHIR_DIR = API_DIR / "var" / "fhir"
ENV_FILES = (REPO_ROOT / ".env", API_DIR / ".env")


def load_dotenv() -> None:
    import os

    for path in ENV_FILES:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
