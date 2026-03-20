import uvicorn

from server.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
    )
