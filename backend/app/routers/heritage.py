# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from app.services.heritage_service import heritage_service

router = APIRouter(tags=["Heritage"])


@router.get("/heritage")
@router.get("/heritage-items")
def list_heritage_items():
    """Lấy danh sách tất cả các hiện vật di sản trong hệ thống."""
    return heritage_service.get_all_heritage()


@router.get("/heritage/{heritage_id}")
def get_heritage_item(heritage_id: str):
    """Lấy thông tin chi tiết một hiện vật di sản theo heritage_id."""
    return heritage_service.get_heritage_by_id(heritage_id)
