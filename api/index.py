"""Vercel Python entry: re-export the FastAPI app (static frontend is served by Vercel)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import app  # noqa: E402,F401
