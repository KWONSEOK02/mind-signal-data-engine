"""2대 헤드셋 동시 연결 E2E 테스트

설정 상수:
- AUTHORIZE_DELAY_SECONDS = 5 (기본값, PARTIAL 시 15로 증가)
- STARTUP_TIMEOUT_SECONDS = 120 (헤드셋 연결 대기 최대 시간)
- MONITOR_DURATION_SECONDS = 30
- GROUP_ID = "testDual" (예약된 테스트 전용 ID — 프로덕션에서 사용 금지)
- MAX_RETRIES = 2 (PARTIAL 시 최대 재시도 횟수)

사용법:
    conda activate mind-signal
    python scripts/test_dual_connection.py
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env.local")

# 테스트 상수 정의함
AUTHORIZE_DELAY_SECONDS = 5
STARTUP_TIMEOUT_SECONDS = 120
MONITOR_DURATION_SECONDS = 30
GROUP_ID = "testDual"  # 예약된 테스트 전용 ID — 프로덕션에서 사용 금지
MAX_RETRIES = 2

PYTHON_PATH = sys.executable
CHANNEL_1 = f"mind-signal:{GROUP_ID}:subject:1"
CHANNEL_2 = f"mind-signal:{GROUP_ID}:subject:2"


def get_redis_client():
    """Redis 클라이언트 생성함"""
    import redis
    from redis.backoff import ExponentialBackoff
    from redis.exceptions import ConnectionError, TimeoutError
    from redis.retry import Retry

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(
        redis_url,
        retry=Retry(ExponentialBackoff(cap=10, base=1), 5),
        retry_on_error=[ConnectionError, TimeoutError, ConnectionResetError],
    )


def run_test(delay_seconds: int) -> str:
    """단일 테스트 라운드 실행함

    Returns:
        "PASS" — 양쪽 채널 모두 데이터 수신
        "PARTIAL" — 한쪽만 수신
        "FAIL" — 양쪽 모두 미수신
    """
    print(f"\n{'=' * 60}")
    print(f"테스트 시작 (delay={delay_seconds}s)")
    print(f"{'=' * 60}")

    p1 = None
    p2 = None
    received = {CHANNEL_1: False, CHANNEL_2: False}

    try:
        # Process 1 spawn 수행함
        print("[1] Process 1 시작 (subject 1)...")
        p1 = subprocess.Popen(
            [PYTHON_PATH, "-m", "core.main", GROUP_ID, "1"],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # authorize 경쟁 조건 회피 대기함
        print(f"[2] {delay_seconds}초 대기 (authorize 경쟁 조건 회피)...")
        time.sleep(delay_seconds)

        # Process 2 spawn 수행함
        print("[3] Process 2 시작 (subject 2)...")
        p2 = subprocess.Popen(
            [PYTHON_PATH, "-m", "core.main", GROUP_ID, "2"],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # startup 타임아웃 내 첫 메시지 대기함
        print(f"[4] 첫 데이터 대기 (최대 {STARTUP_TIMEOUT_SECONDS}초)...")
        r = get_redis_client()
        pubsub = r.pubsub()
        pubsub.subscribe(CHANNEL_1, CHANNEL_2)

        startup_deadline = time.time() + STARTUP_TIMEOUT_SECONDS
        while time.time() < startup_deadline:
            msg = pubsub.get_message(timeout=1)
            if msg and msg["type"] == "message":
                channel = msg["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                if channel in received:
                    received[channel] = True
                    print(f"  [DATA] {channel} — 수신 시작됨")
                if all(received.values()):
                    break

            # 프로세스 조기 종료 감지함
            if p1.poll() is not None and not received[CHANNEL_1]:
                print(f"  [WARN] Process 1 조기 종료 (exit={p1.returncode})")
                break
            if p2 and p2.poll() is not None and not received[CHANNEL_2]:
                print(f"  [WARN] Process 2 조기 종료 (exit={p2.returncode})")
                break

        if not any(received.values()):
            print("[FAIL] startup 타임아웃 — 양쪽 모두 데이터 미수신")
            _print_stderr(p1, p2)
            return "FAIL"

        # 모니터링 구간 수행함
        if all(received.values()):
            print(f"[5] 양쪽 연결 확인됨. {MONITOR_DURATION_SECONDS}초 모니터링...")
            monitor_deadline = time.time() + MONITOR_DURATION_SECONDS
            count = {CHANNEL_1: 0, CHANNEL_2: 0}

            while time.time() < monitor_deadline:
                msg = pubsub.get_message(timeout=1)
                if msg and msg["type"] == "message":
                    channel = msg["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode()
                    if channel in count:
                        count[channel] += 1

            print(f"  채널 1 수신: {count[CHANNEL_1]}건")
            print(f"  채널 2 수신: {count[CHANNEL_2]}건")

            if count[CHANNEL_1] > 0 and count[CHANNEL_2] > 0:
                return "PASS"
            elif count[CHANNEL_1] > 0 or count[CHANNEL_2] > 0:
                return "PARTIAL"
            else:
                return "FAIL"

        # 한쪽만 수신된 경우함
        _print_stderr(p1, p2)
        return "PARTIAL"

    finally:
        # 좀비 프로세스 완전 방지함
        for proc, name in [(p1, "P1"), (p2, "P2")]:
            if proc is not None and proc.poll() is None:
                print(f"  [{name}] terminate 수행함...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


def _print_stderr(p1, p2):
    """프로세스 stderr 출력함 (에러 진단용)"""
    for proc, name in [(p1, "P1"), (p2, "P2")]:
        if proc is not None:
            try:
                stderr = proc.stderr.read().decode("utf-8", errors="replace")
                if stderr.strip():
                    print(f"\n  [{name} stderr]:\n{stderr[:500]}")
            except Exception:
                pass


def main():
    """메인 테스트 루프 실행함"""
    print("EMOTIV 2대 헤드셋 동시 연결 E2E 테스트")
    print(f"그룹 ID: {GROUP_ID} (테스트 전용)")
    print(f"모니터링: {MONITOR_DURATION_SECONDS}초")

    delay = AUTHORIZE_DELAY_SECONDS
    result = "FAIL"

    for attempt in range(MAX_RETRIES + 1):
        if attempt > 0:
            print(f"\n재시도 {attempt}/{MAX_RETRIES} (delay={delay}s)")

        result = run_test(delay)

        if result == "PASS":
            print(f"\n{'=' * 60}")
            print("[PASS] 2대 헤드셋 동시 연결 성공!")
            print(f"{'=' * 60}")
            break
        elif result == "PARTIAL" and attempt < MAX_RETRIES:
            delay = 15  # 증가된 delay로 재시도함
            print(f"\n[PARTIAL] 한쪽만 연결됨. delay {delay}s로 재시도...")
        else:
            break

    if result != "PASS":
        print(f"\n{'=' * 60}")
        print(f"[{result}] 2대 동시 연결 실패.")
        print("대안: PC 2대 분산 아키텍처 (docs/dual-headset-2pc-setup.md)")
        print(f"{'=' * 60}")

    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
