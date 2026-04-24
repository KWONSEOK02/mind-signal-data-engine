"""register_to_backend_dual webhook 단위 테스트 모음"""

import json

import httpx
import pytest
from pytest_httpx import HTTPXMock

from server.services.webhook import register_to_backend_dual

# ──────────────────────────────────────────────
# 테스트 상수
# ──────────────────────────────────────────────
MOCK_BACKEND_URL = "http://mock-backend:5000"
MOCK_ENGINE_URL = "http://192.168.0.10:5002"
MOCK_GROUP_ID = "grp_abc123"
MOCK_SUBJECT_INDEX = 1
MOCK_SECRET_KEY = "test-secret"
REGISTER_DUAL_URL = f"{MOCK_BACKEND_URL}/api/engine/register-dual"


# ──────────────────────────────────────────────
# T7-1: 성공 시 camelCase payload POST 확인
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_register_dual_success(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REGISTRATION_MODE=local + DUAL_2PC env 설정 시 /register-dual 정상 호출함"""
    # settings.backend_url을 mock URL로 교체함
    from server.config import settings

    monkeypatch.setattr(settings, "backend_url", MOCK_BACKEND_URL)

    # BE 200 OK 응답 등록
    httpx_mock.add_response(
        url=REGISTER_DUAL_URL,
        json={"message": "OK", "registeredCount": 1},
        status_code=200,
    )

    await register_to_backend_dual(
        public_url=MOCK_ENGINE_URL,
        group_id=MOCK_GROUP_ID,
        subject_index=MOCK_SUBJECT_INDEX,
        secret_key=MOCK_SECRET_KEY,
    )

    # 전송된 요청 본문 검증 — camelCase 필드명 + 정확한 값
    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert str(request.url) == REGISTER_DUAL_URL
    body = json.loads(request.content)
    assert body == {
        "groupId": MOCK_GROUP_ID,
        "subjectIndex": MOCK_SUBJECT_INDEX,
        "engineUrl": MOCK_ENGINE_URL,
        "secretKey": MOCK_SECRET_KEY,
    }


# ──────────────────────────────────────────────
# T7-2: 403 응답 시 HTTPStatusError raise 확인
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_register_dual_403_raises(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BE가 403 반환 시 httpx.HTTPStatusError raise됨 (secret 불일치 시나리오)"""
    from server.config import settings

    monkeypatch.setattr(settings, "backend_url", MOCK_BACKEND_URL)

    # BE 403 Forbidden 응답 등록
    httpx_mock.add_response(
        url=REGISTER_DUAL_URL,
        status_code=403,
        json={"error": "Forbidden", "message": "Invalid secret key"},
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await register_to_backend_dual(
            public_url=MOCK_ENGINE_URL,
            group_id=MOCK_GROUP_ID,
            subject_index=MOCK_SUBJECT_INDEX,
            secret_key="wrong-secret",
        )

    # 403 상태코드 응답 예외 확인
    assert exc_info.value.response.status_code == 403


# ──────────────────────────────────────────────
# T7-3: 503 단일 응답 시 HTTPStatusError raise 확인
# (webhook.py 자체 retry 없음 — lifespan 레이어가 retry 담당)
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_register_dual_503_raises_no_retry(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """register_to_backend_dual 자체는 retry 없음 — 503 즉시 HTTPStatusError raise됨"""
    from server.config import settings

    monkeypatch.setattr(settings, "backend_url", MOCK_BACKEND_URL)

    # BE 503 Service Unavailable 응답 등록
    httpx_mock.add_response(
        url=REGISTER_DUAL_URL,
        status_code=503,
        json={"error": "Service Unavailable"},
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await register_to_backend_dual(
            public_url=MOCK_ENGINE_URL,
            group_id=MOCK_GROUP_ID,
            subject_index=MOCK_SUBJECT_INDEX,
            secret_key=MOCK_SECRET_KEY,
        )

    # 503 상태코드 응답 예외 확인 — 1회 요청만 발생함
    assert exc_info.value.response.status_code == 503
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
