"""Local dev runner: `python backend/main.py` (or `python main.py` from backend/).

Docker/production uses `uvicorn app.main:app` directly (see Dockerfile CMD).
This launcher exists only so `python backend/main.py` works from any cwd.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure `app.*` is importable regardless of where this script is launched from.
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        port=8000,
        reload=True,
        reload_dirs=[str(BACKEND_DIR / "app")],
    )
