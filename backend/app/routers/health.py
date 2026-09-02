# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from app.services.heritage_service import heritage_service

router = APIRouter(tags=["Health"])


@router.get("/")
def root():
    return {"message": "Tai Sinh Di San So AI API đang chạy"}


@router.get("/health")
def health_check():
    return heritage_service.check_health()
