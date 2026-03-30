from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """서버 상태 확인 엔드포인트임"""
    return {"status": "ok", "service": "mind-signal-data-engine"}
