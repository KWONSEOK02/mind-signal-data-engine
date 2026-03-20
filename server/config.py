from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """환경변수 통합 관리 클래스임"""

    # FastAPI 서버
    port: int = 5002
    use_ngrok: bool = False  # 로컬 개발 시 False, 외부 접근 시 True

    # 백엔드 연동
    backend_url: str = "http://localhost:5000"
    engine_secret_key: str = "change-me-in-production"

    # Emotiv
    client_id: str = ""
    client_secret: str = ""

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # 실험
    experiment_duration_minutes: int = 10

    # 분석 파이프라인 파라미터
    stimulus_duration_sec: int = 60  # 1개 자극의 총 시간 (초)
    window_size_sec: int = 10  # 시간 분할 단위 (초)
    n_stimuli: int = 10  # 전체 자극 수
    n_bands: int = 4  # 사용할 뇌파 대역 수
    baseline_duration_sec: int = 30  # baseline 구간 길이 (초)
    band_cols: list[str] = ["alpha", "beta", "theta", "gamma"]  # 사용할 대역

    # ngrok
    ngrok_auth_token: str = ""

    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"
        extra = "ignore"  # .env.local의 미정의 변수 무시함


settings = Settings()
