import csv
import json
import os
import threading
from datetime import datetime

import redis
from dotenv import load_dotenv

from core.analyzer import MindSignalAnalyzer
from sdk.cortex import Cortex

# 환경 변수 로드
load_dotenv(".env.local")


class MindSignalStreamer(Cortex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.analyzer = MindSignalAnalyzer()

        # 1. 환경 변수에서 실험 시간 읽기 (기본값 10분)
        self.duration_min = int(os.getenv("EXPERIMENT_DURATION_MINUTES", 10))
        self.duration_sec = self.duration_min * 60

        # 2. CSV 저장 경로 및 파일 설정
        # 프로젝트 루트의 csv 폴더를 가리킴 (mind-signal-data-engine/core -> Team-project/csv)
        save_dir = "../../csv"
        os.makedirs(save_dir, exist_ok=True)  # 폴더가 없으면 자동 생성

        self.file_name = os.path.join(
            save_dir, f"brain_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        self.csv_file = open(self.file_name, mode="w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.csv_file)
        self.writer.writerow(
            ["timestamp", "ch1", "ch2", "ch3", "alpha_pwr", "beta_pwr"]
        )

        # 3. Redis 설정
        self.r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
        )
        self.channel = os.getenv("REDIS_CHANNEL", "mind-signal-live")

        # 4. 필수 이벤트 바인딩
        self.bind(create_session_done=self.on_create_session_done)
        self.bind(new_eeg_data=self.on_new_eeg_data)
        self.bind(inform_error=self.on_inform_error)

    def on_create_session_done(self, *args, **kwargs):
        print(f"🚀 세션 연결 성공! {self.duration_min}분 측정을 시작합니다.")
        print(f"📁 저장 파일: {self.file_name}")

        # ⏱️ 자동 종료 타이머 설정
        timer = threading.Timer(self.duration_sec, self.auto_stop)
        timer.start()

        # 데이터 구독 요청
        self.sub_request(["eeg"])

    def on_new_eeg_data(self, *args, **kwargs):
        data = kwargs.get("data")
        eeg_values = data["eeg"]
        timestamp = data["time"]

        # 데이터 분석 (RMS Power 계산)
        alpha_pwr = self.analyzer.get_rms_power(self.analyzer.filter_alpha(eeg_values))
        beta_pwr = self.analyzer.get_rms_power(self.analyzer.filter_beta(eeg_values))

        # 터미널 출력 및 CSV 저장
        print(
            f"📡 기록 중... {timestamp} | Alpha: {alpha_pwr:.2f} | Beta: {beta_pwr:.2f}"
        )
        self.writer.writerow(
            [
                timestamp,
                eeg_values[0],
                eeg_values[1],
                eeg_values[2],
                alpha_pwr,
                beta_pwr,
            ]
        )

        # Redis 전송 (실시간 시각화용)
        payload = {
            "type": "eeg_processed",
            "alpha": alpha_pwr,
            "beta": beta_pwr,
            "time": timestamp,
        }
        self.r.publish(self.channel, json.dumps(payload))

    def auto_stop(self):
        print(f"\n⌛ {self.duration_min}분이 경과하여 측정을 자동으로 종료합니다.")
        self.close()

    def on_inform_error(self, *args, **kwargs):
        error_data = kwargs.get("error_data")
        print(f"❌ 에러 발생: {error_data}")

    def on_close(self, *args, **kwargs):
        if not self.csv_file.closed:
            self.csv_file.close()
        print("🔌 프로그램이 안전하게 종료되었습니다.")


# --- 🚀 실제 엔진 가동부 (필수!) ---
if __name__ == "__main__":
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if not client_id or not client_secret:
        print("❌ .env.local 파일에서 API 키를 확인하세요.")
    else:
        streamer = MindSignalStreamer(client_id, client_secret)
        streamer.open()
