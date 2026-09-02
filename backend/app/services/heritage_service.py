# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse

from app.supabase_client import get_supabase_client


class HeritageService:
    @staticmethod
    def check_health() -> JSONResponse | dict:
        """Kiểm tra kết nối tới Supabase."""
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

    @staticmethod
    def get_all_heritage() -> list[dict]:
        """Lấy danh sách tất cả các hiện vật di sản."""
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

    @staticmethod
    def get_heritage_by_id(heritage_id: str) -> dict:
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

    @staticmethod
    def get_rule_base_by_id(heritage_id: str) -> dict:
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


heritage_service = HeritageService()
