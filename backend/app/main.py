# pyrefly: ignore [missing-import]
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.supabase_client import get_supabase_client

app = FastAPI(title="Tai Sinh Di San So AI Backend")


@app.get("/")
def root():
    return {"message": "Tai Sinh Di San So AI API đang chạy"}


@app.get("/health")
def health_check():
    try:
        client = get_supabase_client()
    except RuntimeError as e:
        return JSONResponse(
            content={"status": "degraded", "supabase": f"not_configured: {e}"},
            status_code=503,
        )

    try:
        client.table("sources").select("source_id").limit(1).execute()
        return {"status": "ok", "supabase": "reachable"}
    except Exception as e:
        return JSONResponse(
            content={"status": "degraded", "supabase": f"error: {type(e).__name__}"},
            status_code=503,
        )


if __name__ == "__main__":
    import sys
    from pathlib import Path
    import uvicorn

    backend_dir = str(Path(__file__).resolve().parent.parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    uvicorn.run("app.main:app", host="127.0.0.1", port=8081, reload=True)
