"""
Vercel serverless entrypoint. Exposes the same FastAPI app used for
local/Docker runs so behavior is identical across environments.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
for sub in ("backend", "financial-engine", "funding-engine"):
    sys.path.insert(0, str(_ROOT / sub))

from app.main import app  # noqa: E402  (Vercel's Python runtime looks for `app`)
