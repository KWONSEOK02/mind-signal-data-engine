from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from server.config import settings
from server.routes import analyze, export, health
from server.services.webhook import register_to_backend

load_dotenv(".env.local")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 pyngrok 터널 + 백엔드 등록 수행함"""
    # --- startup ---
    if settings.use_ngrok:
        from pyngrok import ngrok
        tunnel = ngrok.connect(settings.port, "http")
        app.state.public_url = tunnel.public_url
        print(f"ngrok 퍼블릭 URL 발급됨: {tunnel.public_url}")

        # 백엔드에 자동 등록 수행함
        await register_to_backend(tunnel.public_url, settings.engine_secret_key)
    else:
        app.state.public_url = f"http://localhost:{settings.port}"

    yield

    # --- shutdown ---
    if settings.use_ngrok:
        from pyngrok import ngrok
        ngrok.disconnect(tunnel.public_url)


app = FastAPI(
    title="Mind Signal Data Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router, tags=["Health"])
app.include_router(analyze.router, prefix="/api", tags=["Analyze"])
app.include_router(export.router, prefix="/api", tags=["Export"])
