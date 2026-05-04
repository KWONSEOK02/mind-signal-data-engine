"""register_to_backend_pending / unregister_to_backend_pending 단위 테스트 모음"""

import json

import httpx
import pytest
from pytest_httpx import HTTPXMock

from server.services.webhook import (
    register_to_backend_pending,
    unregister_to_backend_pending,
)

# ──────────────────────────────────────────────
# 테스트 상수
# ──────────────────────────────────────────────
MOCK_BACKEND_URL = "http://mock-backend:5000"
MOCK_ENGINE_URL = "https://superexcited-thad-fluffiest.ngrok-free.dev"
MOCK_SUBJECT_INDEX = 1
MOCK_SECRET_KEY = "test-secret"
REGISTER_PENDING_URL = f"{MOCK_BACKEND_URL}/api/engine/register-pending"


# ──────────────────────────────────────────────
# T1: BE 200 OK → 정상 호출 + camelCase payload 검증
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_register_to_backend_pending_success(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BE 200 응답 시 register_to_backend_pending 정상 호출 + camelCase payload 검증함"""
    from server.config import settings

    monkeypatch.setattr(settings, "backend_url", MOCK_BACKEND_URL)

    # BE 200 OK 응답 등록
    httpx_mock.add_response(
        url=REGISTER_PENDING_URL,
        method="POST",
        json={"message": "OK"},
        status_code=200,
    )

    await register_to_backend_pending(
        public_url=MOCK_ENGINE_URL,
        subject_index=MOCK_SUBJECT_INDEX,
        secret_key=MOCK_SECRET_KEY,
    )

    # 전송된 요청 검증 — POST + camelCase 필드명
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert str(request.url) == REGISTER_PENDING_URL

    body = json.loads(request.content)
    assert body == {
        "subjectIndex": MOCK_SUBJECT_INDEX,
        "engineUrl": MOCK_ENGINE_URL,
        "secretKey": MOCK_SECRET_KEY,
    }


# ──────────────────────────────────────────────
# T2: BE 403 응답 → HTTPStatusError raise 확인 (secret mismatch 시나리오)
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_register_to_backend_pending_403_secret_mismatch(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BE 403 반환 시 httpx.HTTPStatusError raise됨 (secretKey 불일치 시나리오)"""
    from server.config import settings

    monkeypatch.setattr(settings, "backend_url", MOCK_BACKEND_URL)

    # BE 403 Forbidden 응답 등록
    httpx_mock.add_response(
        url=REGISTER_PENDING_URL,
        method="POST",
        status_code=403,
        json={"error": "Forbidden", "message": "Invalid secret key"},
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await register_to_backend_pending(
            public_url=MOCK_ENGINE_URL,
            subject_index=MOCK_SUBJECT_INDEX,
            secret_key="wrong-secret",
        )

    # 403 상태코드 응답 예외 확인
    assert exc_info.value.response.status_code == 403


# ──────────────────────────────────────────────
# T3: BE 미응답(네트워크 에러) → soft-fail 확인 (raise 없음)
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_unregister_pending_soft_fail_on_network_error(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BE 미응답(ConnectError) 시 unregister_to_backend_pending soft-fail — raise 안 함"""
    from server.config import settings

    monkeypatch.setattr(settings, "backend_url", MOCK_BACKEND_URL)

    # 네트워크 에러 시뮬레이션
    httpx_mock.add_exception(
        httpx.ConnectError("Connection refused"),
        url=REGISTER_PENDING_URL,
        method="DELETE",
    )

    # soft-fail이므로 예외 전파 없음 — 정상 반환 기대
    await unregister_to_backend_pending(
        public_url=MOCK_ENGINE_URL,
        subject_index=MOCK_SUBJECT_INDEX,
        secret_key=MOCK_SECRET_KEY,
    )
    # 여기까지 도달하면 soft-fail 성공


# ──────────────────────────────────────────────
# T4: lifespan pending retry — 3회 503 후 soft-fail (SystemExit 없음)
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_lifespan_pending_retry_3times_on_503(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BE 503 3회 연속 → HTTPStatusError raise됨. retry는 lifespan 분기 2가 처리함."""
    from server.config import settings

    monkeypatch.setattr(settings, "backend_url", MOCK_BACKEND_URL)

    # 3회 503 응답 등록 — lifespan retry 루프가 3회 호출함을 전제
    for _ in range(3):
        httpx_mock.add_response(
            url=REGISTER_PENDING_URL,
            method="POST",
            status_code=503,
            json={"error": "Service Unavailable"},
        )

    # lifespan retry 루프 시뮬레이션: asyncio.sleep 패치 (대기 없이 즉시 진행)
    # asyncio.coroutine은 Python 3.11+ 제거됨 → async def noop 사용함
    import asyncio

    async def _noop_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)

    # register_to_backend_pending 자체는 3회 시도 시 마지막에 HTTPStatusError raise
    # lifespan 분기 2는 이 예외를 잡아 soft-fail 처리 — 단위 테스트에서는 raise 확인
    attempt_count = 0
    pending_registered = False
    for attempt in range(3):
        try:
            await register_to_backend_pending(
                public_url=MOCK_ENGINE_URL,
                subject_index=MOCK_SUBJECT_INDEX,
                secret_key=MOCK_SECRET_KEY,
            )
            pending_registered = True
            break
        except Exception:
            attempt_count += 1

    # 3회 모두 실패 → pending_registered=False, SystemExit 없음
    assert attempt_count == 3
    assert pending_registered is False

    # 3회 요청 전송 확인
    requests = httpx_mock.get_requests()
    assert len(requests) == 3
