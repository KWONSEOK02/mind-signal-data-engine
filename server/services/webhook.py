import httpx

from server.config import settings


async def register_to_backend(public_url: str, secret_key: str):
    """백엔드에 엔진 URL + secret_key를 자동 등록함"""
    payload = {
        "engineUrl": public_url,
        "secretKey": secret_key,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.backend_url}/api/engine/register",
                json=payload,
            )
            if response.status_code == 200:
                print(f"백엔드 등록 성공함: {public_url}")
            else:
                print(f"백엔드 등록 실패함: {response.status_code} {response.text}")
    except httpx.RequestError as e:
        print(f"백엔드 연결 실패함: {e}")
