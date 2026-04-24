import asyncio

import httpx

from server.config import settings

# heartbeat 주기 (초) — Heroku dyno sleep 대비 5분마다 재등록함
HEARTBEAT_INTERVAL_SEC = 300


async def register_to_backend(public_url: str, secret_key: str) -> None:
    """백엔드에 엔진 URL + secret_key를 자동 등록함"""
    payload = {
        "engineUrl": public_url,
        "secretKey": secret_key,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{settings.backend_url}/api/engine/register",
            json=payload,
        )
        # RC-7: silent catch 제거 — 실패 시 예외 전파해 lifespan SystemExit 트리거
        response.raise_for_status()
    print(f"백엔드 등록 성공함: {public_url}")


async def register_to_backend_dual(
    public_url: str,
    group_id: str,
    subject_index: int,
    secret_key: str,
) -> None:
    """DUAL_2PC 모드: groupId+subjectIndex 기반 BE 등록."""
    payload = {
        "groupId": group_id,
        "subjectIndex": subject_index,
        "engineUrl": public_url,
        "secretKey": secret_key,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{settings.backend_url}/api/engine/register-dual",
            json=payload,
        )
        response.raise_for_status()
    # [RC3-1 반영] DE 서버 전체가 print() 사용 — 기존 convention 유지
    print(
        f"DUAL_2PC register success: groupId={group_id}, "
        f"subjectIndex={subject_index}, url={public_url}"
    )


async def start_heartbeat(public_url: str, secret_key: str):
    """주기적으로 백엔드에 엔진 URL을 재등록하는 heartbeat 태스크임"""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
        try:
            await register_to_backend(public_url, secret_key)
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            # heartbeat는 transient error 허용 (log-and-continue)
            # R2-1: register_to_backend가 RC-7로 naked 됐으므로 여기서 명시 보호
            # [RC3-1 반영] DE 서버 전체가 print() 사용 — 기존 convention 유지
            print(f"heartbeat register failed (non-fatal): {e}")
