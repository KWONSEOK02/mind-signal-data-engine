"""EEG 스트리밍 관리 엔드포인트임"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from server.config import settings
from server.services.stream import get_all_status, start_stream, stop_stream

router = APIRouter()


class StreamStartRequest(BaseModel):
    group_id: str
    subject_index: int


class StreamStopRequest(BaseModel):
    group_id: str
    subject_index: int


@router.post("/stream/start")
async def stream_start(
    body: StreamStartRequest,
    x_engine_secret: str = Header(alias="X-Engine-Secret"),
):
    """core.main을 spawn하여 EEG 스트리밍 시작함"""
    if x_engine_secret != settings.engine_secret_key:
        raise HTTPException(status_code=403, detail="인증 실패: 유효하지 않은 시크릿 키임")

    try:
        result = start_stream(body.group_id, body.subject_index)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return result


@router.post("/stream/stop")
async def stream_stop(
    body: StreamStopRequest,
    x_engine_secret: str = Header(alias="X-Engine-Secret"),
):
    """실행 중인 EEG 스트리밍 종료함"""
    if x_engine_secret != settings.engine_secret_key:
        raise HTTPException(status_code=403, detail="인증 실패: 유효하지 않은 시크릿 키임")

    try:
        result = stop_stream(body.group_id, body.subject_index)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result


@router.get("/stream/status")
async def stream_status(
    x_engine_secret: str = Header(alias="X-Engine-Secret"),
):
    """모든 스트리밍 프로세스 상태 조회함"""
    if x_engine_secret != settings.engine_secret_key:
        raise HTTPException(status_code=403, detail="인증 실패: 유효하지 않은 시크릿 키임")

    return get_all_status()
