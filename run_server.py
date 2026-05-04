import os

# Phase 17.5.3 — Windows uvicorn reloader 환경에서 print() stdout buffering으로
# lifespan 로그가 누락되는 현상 방지함. reloader process가 worker stdout을 pipe
# forwarding하는 과정에서 flush 지연 + 터미널 라인 잘림 발생 가능.
os.environ.setdefault("PYTHONUNBUFFERED", "1")

import uvicorn  # noqa: E402

from server.config import settings  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=settings.fastapi_port,
        reload=True,
    )
