"""SIH repository entry point for the DeCypher FastAPI backend.

The production implementation remains in backend/app/. This small adapter keeps
an SIH-compatible src/main.py entry point without moving the working backend.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

__all__ = ["app"]
