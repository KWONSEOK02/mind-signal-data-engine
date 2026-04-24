import asyncio
import socket
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from server.config import settings
from server.routes import analyze, control, export, health, stream
from server.services.webhook import (
    register_to_backend,
    register_to_backend_dual,
    start_heartbeat,
    start_heartbeat_dual,
)

load_dotenv(".env.local")

# Preflight soft-check: ENGINE_SECRET_KEY가 placeholder면 WARNING 로그만 출력함
# (Phase 17.5.1 — abort 제거). 실기기 테스트 등 placeholder 그대로 쓰다가 실험 후
# 보완하는 흐름을 허용함. 공개 ngrok URL에 /control/assign-group 노출 리스크는
# 경고로만 안내함
PLACEHOLDER_SECRETS = {
    "your-shared-secret-here",
    "change-me-in-production",
    "",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 URL 결정 + 백엔드 등록(모드별 분기) + heartbeat 수행함.

    분기 (Phase 17.5 도입):
    1) dual_2pc_group_id + subject_index 둘 다 env → 즉시 register-dual +
       dual heartbeat (backward-compat)
    2) subject_index만 env → pending 상태 기동 → /control/assign-group 대기
       (heartbeat 미생성)
    3) 둘 다 없음 → SEQUENTIAL register + single heartbeat (backward-compat)
    """
    # Preflight soft-check: placeholder secret 감지 시 WARNING만 출력함 (Phase 17.5.1)
    if settings.engine_secret_key in PLACEHOLDER_SECRETS:
        print(
            "[WARN] ENGINE_SECRET_KEY가 placeholder 값임 "
            f"('{settings.engine_secret_key}'). /control/assign-group이 "
            "공개 ngrok URL에서 사실상 검증 없이 열림. 실기기 테스트 후 "
            "실제 값으로 교체 권장함."
        )

    # public_url 결정 (registration_mode 기반)
    if settings.registration_mode == "ngrok":
        from pyngrok import ngrok

        tunnel = ngrok.connect(settings.fastapi_port, bind_tls=True)
        public_url = tunnel.public_url
        print(f"ngrok 퍼블릭 URL 발급됨: {public_url}", flush=True)
    else:  # local
        lan_ip = settings.lan_ip or socket.gethostbyname(socket.gethostname())
        public_url = f"http://{lan_ip}:{settings.fastapi_port}"

    # app.state 초기화 (Phase 17.5) — 모든 분기 공통
    app.state.public_url = public_url
    app.state.subject_index = settings.dual_2pc_subject_index
    app.state.secret_key = settings.engine_secret_key
    app.state.registered_group_id = None
    app.state.heartbeat_task = None  # 분기 2는 미생성 → shutdown 가드용
    app.state.assign_lock = asyncio.Lock()

    # 모드 판별 — 빈 문자열("") env를 None과 동등하게 취급함 (Phase 17.5.2)
    # pydantic이 `DUAL_2PC_GROUP_ID=` 빈 값을 ""로 파싱해 is not None 통과하는 버그 방지
    has_group_id = bool(settings.dual_2pc_group_id)
    has_subject_index = settings.dual_2pc_subject_index is not None

    try:
        if has_group_id and has_subject_index:
            # 분기 1: 즉시 DUAL_2PC 등록
            await register_to_backend_dual(
                public_url,
                settings.dual_2pc_group_id,
                settings.dual_2pc_subject_index,
                settings.engine_secret_key,
            )
            app.state.registered_group_id = settings.dual_2pc_group_id
            app.state.heartbeat_task = asyncio.create_task(
                start_heartbeat_dual(
                    public_url,
                    settings.dual_2pc_group_id,
                    settings.dual_2pc_subject_index,
                    settings.engine_secret_key,
                )
            )
        elif has_subject_index:
            # 분기 2: pending — BE 등록 하지 않음. /control/assign-group 대기함
            print(
                f"DE pending: subject_index={settings.dual_2pc_subject_index}, "
                f"awaiting POST /control/assign-group"
            )
        else:
            # 분기 3: SEQUENTIAL (backward-compat)
            await register_to_backend(public_url, settings.engine_secret_key)
            app.state.heartbeat_task = asyncio.create_task(
                start_heartbeat(public_url, settings.engine_secret_key)
            )
    except Exception as e:
        # [RC3-1 반영] DE 서버 전체가 print() 사용 — 기존 convention 유지
        print(f"DE registration failed: {e}")
        raise SystemExit(1)

    yield

    # --- shutdown ---
    # heartbeat_task 가드 (분기 2는 None 가능)
    if app.state.heartbeat_task is not None:
        app.state.heartbeat_task.cancel()

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
app.include_router(control.router, tags=["Control"])
