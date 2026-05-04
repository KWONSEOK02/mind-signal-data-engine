"""Control 라우터 — DUAL_2PC runtime groupId 주입 엔드포인트 제공함 (Phase 17.5)"""

import asyncio

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from server.services.webhook import (
    register_to_backend_dual,
    start_heartbeat_dual,
)

router = APIRouter()


class AssignGroupRequest(BaseModel):
    """/control/assign-group 요청 바디 스키마임"""

    group_id: str = Field(
        ..., min_length=1, description="DUAL_2PC groupId (MongoDB ObjectId 24자 hex)"
    )


@router.post("/control/assign-group")
async def assign_group(
    body: AssignGroupRequest,
    request: Request,
    x_engine_secret: str = Header(alias="X-Engine-Secret"),
):
    """DUAL_2PC groupId 런타임 주입 + BE /register-dual 트리거 처리함.

    멱등 계약:
    - pending → register-dual 호출 후 200 registered + heartbeat 시작함
    - same group_id 재호출 → 200 already_registered (register 재호출 금지, heartbeat 재생성 금지)
    - different group_id → 409 group_id_conflict 반환함
    - secret mismatch → 401 invalid_secret 반환함
    - BE 실패 → 502 backend_register_failed 반환함 + state는 pending 유지(재시도 가능)

    asyncio.Lock으로 race 방지함 — 동시 2건 요청 시 직렬화 처리함.
    """
    app = request.app

    # secret 검증 (401)
    if x_engine_secret != app.state.secret_key:
        raise HTTPException(status_code=401, detail={"error": "invalid_secret"})

    # subject_index 설정 여부 확인 (pending 모드가 아니면 config 에러)
    if app.state.subject_index is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "not_pending_mode",
                "reason": "DUAL_2PC_SUBJECT_INDEX env 필수",
            },
        )

    # Lock 내부에서 state 전이 — race 방지함
    async with app.state.assign_lock:
        current = app.state.registered_group_id

        # 멱등: same group_id → backend 재호출 금지, heartbeat 재생성 금지
        if current == body.group_id:
            return {"status": "already_registered", "groupId": body.group_id}

        # 다른 groupId 이미 등록됨 → 409
        if current is not None:
            raise HTTPException(
                status_code=409,
                detail={"error": "group_id_conflict", "current": current},
            )

        # 신규 등록 경로: BE /register-dual 호출함
        try:
            await register_to_backend_dual(
                app.state.public_url,
                body.group_id,
                app.state.subject_index,
                app.state.secret_key,
            )
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            # 실패 시 state pending 유지 (재시도 허용함)
            raise HTTPException(
                status_code=502,
                detail={"error": "backend_register_failed", "detail": str(e)},
            )

        # 등록 성공 — state 업데이트 + heartbeat 시작함
        app.state.registered_group_id = body.group_id
        app.state.heartbeat_task = asyncio.create_task(
            start_heartbeat_dual(
                app.state.public_url,
                body.group_id,
                app.state.subject_index,
                app.state.secret_key,
            )
        )

        return {"status": "registered", "groupId": body.group_id}
