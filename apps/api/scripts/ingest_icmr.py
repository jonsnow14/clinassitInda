"""python -m app.rag.ingest  (preferred) or python scripts/ingest_icmr.py from apps/api."""

from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_DIR))

from app.paths import load_dotenv  # noqa: E402
from app.rag.ingest import main  # noqa: E402

if __name__ == "__main__":
    load_dotenv()
    main()
