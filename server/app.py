import asyncio
import socket
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from server.config import settings
from server.routes import analyze, export, health, stream
from server.services.webhook import (
    register_to_backend,
    register_to_backend_dual,
    register_to_backend_pending,
    start_heartbeat,
    unregister_to_backend_pending,
)

load_dotenv(".env.local")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 URL 결정 + 백엔드 등록 + heartbeat 수행함"""
    # --- startup ---

    # public_url 결정 (registration_mode 기반)
    if settings.registration_mode == "ngrok":
        from pyngrok import ngrok

        tunnel = ngrok.connect(settings.fastapi_port, bind_tls=True)
        public_url = tunnel.public_url
        print(f"ngrok 퍼블릭 URL 발급됨: {public_url}")
    else:  # local
        lan_ip = settings.lan_ip or socket.gethostbyname(socket.gethostname())
        public_url = f"http://{lan_ip}:{settings.fastapi_port}"

    app.state.public_url = public_url

    # DUAL_2PC 모드 판별 (env 주입 여부)
    is_dual_2pc = (
        settings.dual_2pc_group_id is not None
        and settings.dual_2pc_subject_index is not None
    )
    # pending mode 판별: subject_index만 주입, group_id 미정 상태
    has_subject_index = (
        settings.dual_2pc_subject_index is not None
        and settings.dual_2pc_group_id is None
    )

    try:
        if is_dual_2pc:
            # 분기 1: groupId + subjectIndex 모두 확정 — register_to_backend_dual 호출함
            await register_to_backend_dual(
                public_url,
                settings.dual_2pc_group_id,
                settings.dual_2pc_subject_index,
                settings.engine_secret_key,
            )
        else:
            await register_to_backend(public_url, settings.engine_secret_key)
    except Exception as e:
        # [RC3-1 반영] DE 서버 전체가 print() 사용 — 기존 convention 유지
        print(f"DE registration failed: {e}")
        raise SystemExit(1)

    # Phase 17.6 LD-22/LD-18: 분기 2 — pending mode (groupId 미정, subjectIndex만 있음)
    # 독립 try/except로 외부 SystemExit 전파 차단함
    if has_subject_index:
        pending_registered = False
        for attempt in range(3):
            try:
                await register_to_backend_pending(
                    public_url,
                    settings.dual_2pc_subject_index,
                    settings.engine_secret_key,
                )
                pending_registered = True
                break
            except Exception as e:  # 분기 2 내부 catch — 외부 SystemExit 차단함
                print(
                    f"[WARN] pending registration attempt {attempt + 1}/3 실패함: {e}"
                )
                if attempt < 2:
                    await asyncio.sleep(2**attempt)  # 1s, 2s
        if not pending_registered:
            print(
                "[WARN] pending registration 3회 실패함. DE 계속 실행, "
                "수동 fallback 의존."
            )
        # 분기 2 내부 raise 금지 — yield까지 정상 진행
        app.state.pending_registered = pending_registered
    else:
        app.state.pending_registered = False

    # heartbeat task (기존 — 5분마다 백엔드에 재등록)
    heartbeat_task = asyncio.create_task(
        start_heartbeat(public_url, settings.engine_secret_key)
    )

    yield

    # --- shutdown ---
    heartbeat_task.cancel()

    # Phase 17.6 LD-26: pending entry 삭제 호출함 (DE shutdown 시 soft-fail)
    if has_subject_index and getattr(app.state, "pending_registered", False):
        await unregister_to_backend_pending(
            app.state.public_url,
            settings.dual_2pc_subject_index,
            settings.engine_secret_key,
        )

    if settings.registration_mode == "ngrok":
        from pyngrok import ngrok

        ngrok.disconnect(public_url)


app = FastAPI(
    title="Mind Signal Data Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router, tags=["Health"])
app.include_router(analyze.router, prefix="/api", tags=["Analyze"])
app.include_router(export.router, prefix="/api", tags=["Export"])
app.include_router(stream.router, prefix="/api", tags=["Stream"])
