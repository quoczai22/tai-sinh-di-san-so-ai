# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from app.services.heritage_service import heritage_service

router = APIRouter(tags=["Rule Base"])


@router.get("/heritage/{heritage_id}/rule-base")
@router.get("/rule-base/{heritage_id}")
def get_rule_base_by_id(heritage_id: str):
    """Lấy Source-Grounded Cultural Rule Base cho hiện vật theo heritage_id qua RPC get_rule_base.

    Đặc tính Fail-closed: Nếu heritage_id không tồn tại hoặc RPC trả null,
    trả về HTTP 404 rõ ràng; tuyệt đối không fallback về Rule Base rỗng.
    """
    return heritage_service.get_rule_base_by_id(heritage_id)
