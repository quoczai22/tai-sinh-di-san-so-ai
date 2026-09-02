# pyrefly: ignore [missing-import]
from fastapi import FastAPI

from app.routers import health, heritage, rule_base

app = FastAPI(
    title="Tai Sinh Di San So AI Backend",
    description="Backend API cho dự án Tái sinh Di sản Số AI — Gốm Bát Tràng",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(heritage.router)
app.include_router(rule_base.router)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    import uvicorn

    backend_dir = str(Path(__file__).resolve().parent.parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    uvicorn.run("app.main:app", host="127.0.0.1", port=8081, reload=True)
