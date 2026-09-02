# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from app.supabase_client import get_supabase_client

app = FastAPI(
    title="Tai Sinh Di San So AI Backend",
    description="Backend API cho dự án Tái sinh Di sản Số AI — Gốm Bát Tràng",
    version="1.0.0",
)


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
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        client.table("sources").select("source_id").limit(1).execute()
        return {"status": "ok", "supabase": "reachable"}
    except Exception as e:
        return JSONResponse(
            content={"status": "degraded", "supabase": f"error: {type(e).__name__}"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


@app.get("/heritage", tags=["Heritage"])
@app.get("/heritage-items", tags=["Heritage"])
def list_heritage_items():
    """Lấy danh sách tất cả các hiện vật di sản trong hệ thống."""
    try:
        client = get_supabase_client()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cấu hình cơ sở dữ liệu chưa sẵn sàng: {e}",
        ) from e

    try:
        response = client.table("heritage_items").select("*").order("heritage_id").execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi truy vấn danh sách di sản: {type(e).__name__}",
        ) from e


@app.get("/heritage/{heritage_id}", tags=["Heritage"])
def get_heritage_item(heritage_id: str):
    """Lấy thông tin chi tiết một hiện vật di sản theo heritage_id."""
    try:
        client = get_supabase_client()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cấu hình cơ sở dữ liệu chưa sẵn sàng: {e}",
        ) from e

    try:
        response = (
            client.table("heritage_items")
            .select("*")
            .eq("heritage_id", heritage_id)
            .execute()
        )
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"heritage_id '{heritage_id}' không tồn tại trong hệ thống",
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi truy vấn hiện vật di sản: {type(e).__name__}",
        ) from e


@app.get("/heritage/{heritage_id}/rule-base", tags=["Rule Base"])
@app.get("/rule-base/{heritage_id}", tags=["Rule Base"])
def get_rule_base_by_id(heritage_id: str):
    """Lấy Source-Grounded Cultural Rule Base cho hiện vật theo heritage_id qua RPC get_rule_base.

    Đặc tính Fail-closed: Nếu heritage_id không tồn tại hoặc RPC trả null,
    trả về HTTP 404 rõ ràng; tuyệt đối không fallback về Rule Base rỗng.
    """
    try:
        client = get_supabase_client()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cấu hình cơ sở dữ liệu chưa sẵn sàng: {e}",
        ) from e

    try:
        rpc_response = client.rpc("get_rule_base", {"p_heritage_id": heritage_id}).execute()
        rule_base = rpc_response.data

        if rule_base is None:
            # Fail-closed: Không tồn tại trong heritage_items -> Báo lỗi, không trả object rỗng
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"heritage_id '{heritage_id}' không tồn tại trong hệ thống (Rule Base không xác định)",
            )

        return rule_base
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi lấy Rule Base: {type(e).__name__}",
        ) from e


if __name__ == "__main__":
    import sys
    from pathlib import Path
    import uvicorn

    backend_dir = str(Path(__file__).resolve().parent.parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    uvicorn.run("app.main:app", host="127.0.0.1", port=8081, reload=True)
