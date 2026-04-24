"""lifespan 3분기 + preflight + shutdown 가드 pytest (Phase 17.5)"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi import FastAPI

from server.config import settings
from server.services import webhook

TEST_VALID_SECRET = "test-valid-secret"
TEST_GROUP_ID = "507f1f77bcf86cd799439011"
BACKEND_URL = f"{settings.backend_url}/api/engine/register"
BACKEND_DUAL_URL = f"{settings.backend_url}/api/engine/register-dual"


@asynccontextmanager
async def _run_lifespan(app: FastAPI):
    """lifespan contextmanager 래퍼 — startup + yield + shutdown 수행함"""
    async with app.router.lifespan_context(app):
        yield


def _import_fresh_app():
    """import 캐시 bypass 후 server.app 모듈 재로딩함"""
    import importlib

    import server.app as mod

    return importlib.reload(mod)


@pytest.mark.asyncio
async def test_lifespan_placeholder_secret_aborts(monkeypatch):
    """preflight hard-gate — placeholder secret 감지 시 SystemExit(1) 발생 확인함"""
    monkeypatch.setattr(settings, "engine_secret_key", "your-shared-secret-here")
    monkeypatch.setattr(settings, "dual_2pc_group_id", None)
    monkeypatch.setattr(settings, "dual_2pc_subject_index", None)

    mod = _import_fresh_app()

    with pytest.raises(SystemExit) as exc_info:
        async with _run_lifespan(mod.app):
            pass
    assert exc_info.value.code == 1


@pytest.mark.asyncio
async def test_lifespan_dual_env_immediate_register(monkeypatch, httpx_mock):
    """분기 1 — dual env 둘 다 있음 → register-dual 즉시 호출 + heartbeat 생성 확인함"""
    monkeypatch.setattr(settings, "engine_secret_key", TEST_VALID_SECRET)
    monkeypatch.setattr(settings, "dual_2pc_group_id", TEST_GROUP_ID)
    monkeypatch.setattr(settings, "dual_2pc_subject_index", 1)
    monkeypatch.setattr(settings, "registration_mode", "local")
    monkeypatch.setattr(settings, "lan_ip", "127.0.0.1")

    httpx_mock.add_response(url=BACKEND_DUAL_URL, method="POST", status_code=200)

    # HEARTBEAT_INTERVAL_SEC을 길게 (테스트 중 tick 발생 방지)
    with patch.object(webhook, "HEARTBEAT_INTERVAL_SEC", 3600):
        mod = _import_fresh_app()
        async with _run_lifespan(mod.app):
            assert mod.app.state.registered_group_id == TEST_GROUP_ID
            assert mod.app.state.heartbeat_task is not None
            assert not mod.app.state.heartbeat_task.done()


@pytest.mark.asyncio
async def test_lifespan_pending_no_register_no_heartbeat(monkeypatch):
    """분기 2 — subject_index만 있음 → 등록 안 함 + heartbeat None 확인함"""
    monkeypatch.setattr(settings, "engine_secret_key", TEST_VALID_SECRET)
    monkeypatch.setattr(settings, "dual_2pc_group_id", None)
    monkeypatch.setattr(settings, "dual_2pc_subject_index", 2)
    monkeypatch.setattr(settings, "registration_mode", "local")
    monkeypatch.setattr(settings, "lan_ip", "127.0.0.1")

    mod = _import_fresh_app()
    async with _run_lifespan(mod.app):
        assert mod.app.state.registered_group_id is None
        assert mod.app.state.heartbeat_task is None
        assert mod.app.state.subject_index == 2
        # assign_lock이 초기화됨 확인함
        assert isinstance(mod.app.state.assign_lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_lifespan_pending_shutdown_no_crash(monkeypatch):
    """분기 2 shutdown crash 방지 — heartbeat_task None 가드 확인함 (rev.2 C-NEW-1)"""
    monkeypatch.setattr(settings, "engine_secret_key", TEST_VALID_SECRET)
    monkeypatch.setattr(settings, "dual_2pc_group_id", None)
    monkeypatch.setattr(settings, "dual_2pc_subject_index", 1)
    monkeypatch.setattr(settings, "registration_mode", "local")
    monkeypatch.setattr(settings, "lan_ip", "127.0.0.1")

    mod = _import_fresh_app()
    # shutdown 시 heartbeat_task가 None이어도 AttributeError/UnboundLocalError 없이 종료해야 함
    async with _run_lifespan(mod.app):
        assert mod.app.state.heartbeat_task is None
    # 여기까지 도달하면 shutdown 정상 종료 확인됨


@pytest.mark.asyncio
async def test_lifespan_single_legacy_register(monkeypatch, httpx_mock):
    """분기 3 — 둘 다 없음 → SEQUENTIAL register + single heartbeat 확인함"""
    monkeypatch.setattr(settings, "engine_secret_key", TEST_VALID_SECRET)
    monkeypatch.setattr(settings, "dual_2pc_group_id", None)
    monkeypatch.setattr(settings, "dual_2pc_subject_index", None)
    monkeypatch.setattr(settings, "registration_mode", "local")
    monkeypatch.setattr(settings, "lan_ip", "127.0.0.1")

    httpx_mock.add_response(url=BACKEND_URL, method="POST", status_code=200)

    with patch.object(webhook, "HEARTBEAT_INTERVAL_SEC", 3600):
        mod = _import_fresh_app()
        async with _run_lifespan(mod.app):
            assert mod.app.state.registered_group_id is None
            assert mod.app.state.heartbeat_task is not None
            # heartbeat는 single mode — dual이 아닌 legacy register 대상
            assert not mod.app.state.heartbeat_task.done()
