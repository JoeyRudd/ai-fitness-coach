"""Module entry point.
Run with: python -m backend
This starts the FastAPI app defined in app.main:app
"""
from __future__ import annotations

import os
import uvicorn


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_opt = os.getenv("RELOAD", "1") == "1"
    uvicorn.run("app.main:app", host=host, port=port, reload=reload_opt)


if __name__ == "__main__":  # pragma: no cover
    main()
