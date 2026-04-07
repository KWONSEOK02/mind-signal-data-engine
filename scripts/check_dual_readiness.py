"""2대 헤드셋 동시 연결 사전 진단 스크립트

DiagnosticCortex(Cortex) 상속 클래스로 getLicenseInfo 추가 구현함.
sdk/cortex.py 파일 자체는 수정하지 않으며 상속을 통해 확장함.
TLS 인증서는 부모 클래스가 certificates/rootCA.pem으로 자동 처리함.

확인 항목:
1. Cortex 서비스 연결 가능 여부 (wss://localhost:6868)
2. authorize + getLicenseInfo → localQuota 확인
3. queryHeadsets → 헤드셋 2대 discovered 확인
4. HEADSET_ID_1, HEADSET_ID_2 환경변수 설정 및 유니크 확인
5. 각 HEADSET_ID가 discovered 목록에 존재하는지 매칭
6. REDIS_URL이 Upstash(rediss://) 프리픽스인지 확인

사용법:
    conda activate mind-signal
    python scripts/check_dual_readiness.py
"""

import json
import os
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 루트를 sys.path에 추가함
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env.local")

from sdk.cortex import Cortex  # noqa: E402

GET_LICENSE_INFO_ID = 100


class DiagnosticCortex(Cortex):
    """진단 전용 Cortex 확장 클래스 — getLicenseInfo 추가 구현함"""

    def __init__(self, *args, **kwargs):
        kwargs["auto_create_session"] = False
        super().__init__(*args, **kwargs)
        self.license_info = None
        self.headset_list_result = None
        self._diag_done = threading.Event()

    def _get_result_handler(self, req_id):
        """SDK 디스패치 테이블에 getLicenseInfo 핸들러 등록함"""
        if req_id == GET_LICENSE_INFO_ID:
            return self._handle_get_license_info
        return super()._get_result_handler(req_id)

    def get_license_info(self):
        """getLicenseInfo JSON-RPC 호출 수행함"""
        request = {
            "jsonrpc": "2.0",
            "method": "getLicenseInfo",
            "params": {"cortexToken": self.auth},
            "id": GET_LICENSE_INFO_ID,
        }
        self.ws.send(json.dumps(request))

    def _handle_get_license_info(self, result_dic):
        """getLicenseInfo 응답 처리함"""
        self.license_info = result_dic
        if self.headset_list_result is not None:
            self._diag_done.set()

    def _handle_authorize(self, result_dic):
        """authorize 성공 후 getLicenseInfo + queryHeadsets 호출함"""
        print("[OK] Authorize 성공함.")
        self.auth = result_dic["cortexToken"]
        # 부모 상태 보존 후 추가 호출 수행함
        self.get_license_info()
        self.refresh_headset_list()
        self.query_headset()

    def _handle_query_headset(self, result_dic):
        """queryHeadsets 결과 저장함 (연결 시도 안 함)"""
        self.headset_list_result = result_dic
        if self.license_info is not None:
            self._diag_done.set()


def run_diagnostics():
    """진단 항목 전체 실행함"""
    print("=" * 60)
    print("EMOTIV 2대 헤드셋 동시 연결 — 사전 진단")
    print("=" * 60)

    # 1. 환경변수 확인함
    client_id = os.getenv("CLIENT_ID", "")
    client_secret = os.getenv("CLIENT_SECRET", "")
    headset_id_1 = os.getenv("HEADSET_ID_1", "")
    headset_id_2 = os.getenv("HEADSET_ID_2", "")
    redis_url = os.getenv("REDIS_URL", "")

    print("\n[1] 환경변수 확인")
    results = []

    if client_id and client_secret:
        results.append(("[OK]", "CLIENT_ID/SECRET", "설정됨"))
    else:
        results.append(("[FAIL]", "CLIENT_ID/SECRET", "미설정"))

    if headset_id_1:
        results.append(("[OK]", "HEADSET_ID_1", headset_id_1))
    else:
        results.append(("[FAIL]", "HEADSET_ID_1", "미설정"))

    if headset_id_2:
        results.append(("[OK]", "HEADSET_ID_2", headset_id_2))
    else:
        results.append(("[FAIL]", "HEADSET_ID_2", "미설정"))

    if headset_id_1 and headset_id_2 and headset_id_1 == headset_id_2:
        results.append(
            ("[FAIL]", "HEADSET_ID 유니크", "동일값 — 같은 헤드셋에 2세션 불가")
        )
    elif headset_id_1 and headset_id_2:
        results.append(("[OK]", "HEADSET_ID 유니크", "서로 다른 값"))

    if redis_url.startswith("rediss://"):
        results.append(("[OK]", "REDIS_URL", "Upstash TLS (rediss://)"))
    elif redis_url.startswith("redis://"):
        results.append(
            ("[WARN]", "REDIS_URL", "localhost Redis — PC 2대 분산 시 접근 불가")
        )
    else:
        results.append(("[FAIL]", "REDIS_URL", "미설정"))

    for status, key, value in results:
        print(f"  {status} {key}: {value}")

    # 환경변수 FAIL이면 조기 종료함
    has_fail = any(r[0] == "[FAIL]" for r in results)
    if has_fail:
        print("\n[ABORT] 필수 환경변수 미설정. .env.local 확인 필요.")
        return False

    # 2. Cortex 연결 + getLicenseInfo + queryHeadsets 수행함
    print("\n[2] Cortex 서비스 연결 + 라이선스 확인")

    diag = DiagnosticCortex(client_id, client_secret)

    # 백그라운드 스레드에서 실행함 (open()이 blocking)
    ws_thread = threading.Thread(target=diag.open, daemon=True)
    ws_thread.start()

    # 최대 30초 대기함
    if not diag._diag_done.wait(timeout=30):
        print("  [FAIL] Cortex 연결 타임아웃 (30초). Launcher 실행 중인지 확인.")
        return False

    # 라이선스 정보 출력함
    if diag.license_info:
        li = diag.license_info
        local_quota = li.get("localQuota", "N/A")
        device_info = li.get("deviceInfo", {})
        device_limit = device_info.get("deviceLimit", "N/A")
        session_limit = device_info.get("sessionLimit", "N/A")
        print(f"  [OK] localQuota: {local_quota}")
        print(f"  [OK] deviceLimit: {device_limit}")
        print(f"  [OK] sessionLimit: {session_limit}")

        if isinstance(local_quota, (int, float)) and local_quota <= 0:
            print("  [FAIL] localQuota 고갈됨. authorize(debit=N)으로 충전 필요.")
    else:
        print("  [FAIL] getLicenseInfo 응답 없음.")

    # 3. 헤드셋 목록 확인함
    print("\n[3] 헤드셋 목록 확인")
    if diag.headset_list_result:
        headsets = diag.headset_list_result
        print(f"  발견된 헤드셋: {len(headsets)}대")
        for hs in headsets:
            hs_id = hs.get("id", "?")
            status = hs.get("status", "?")
            match_1 = " ← HEADSET_ID_1" if hs_id == headset_id_1 else ""
            match_2 = " ← HEADSET_ID_2" if hs_id == headset_id_2 else ""
            print(f"  - {hs_id} (status: {status}){match_1}{match_2}")

        found_ids = {hs.get("id") for hs in headsets}
        if headset_id_1 not in found_ids:
            print(f"  [FAIL] HEADSET_ID_1 ({headset_id_1}) 미발견")
        if headset_id_2 not in found_ids:
            print(f"  [FAIL] HEADSET_ID_2 ({headset_id_2}) 미발견")

        if headset_id_1 in found_ids and headset_id_2 in found_ids:
            print("  [OK] 양쪽 헤드셋 모두 발견됨")
    else:
        print("  [FAIL] queryHeadsets 응답 없음.")

    # 정리함
    try:
        diag.close()
    except Exception:
        pass

    # 4. 종합 결과 출력함
    print("\n" + "=" * 60)
    print("진단 완료. 위 결과를 확인 후 테스트를 진행하세요.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)
