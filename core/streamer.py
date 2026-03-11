import csv
import json
import os
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
import redis
from dotenv import load_dotenv

from core.analyzer import MindSignalAnalyzer
from sdk.cortex import Cortex

# 환경 변수 로드 수행함
load_dotenv(".env.local")


class MindSignalStreamer(Cortex):
    """
    [Engine] EEG 시계열 버퍼링 및 분석을 통해 실시간 데이터를 발행하는 스트리머임
    """

    def __init__(self, group_id, subject_index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.analyzer = MindSignalAnalyzer()

        # 1. 식별 정보 및 실험 설정 저장함
        self.group_id = group_id
        try:
            self.subject_index = int(subject_index)
        except ValueError:
            self.subject_index = 0

        self.duration_min = int(os.getenv("EXPERIMENT_DURATION_MINUTES", 10))
        self.duration_sec = self.duration_min * 60

        # 2. Redis 채널 설정 및 연결 수행함
        self.channel = f"mind-signal:{self.group_id}:subject:{self.subject_index}"
        self.r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
        )

        # 3. CSV 저장 경로 및 헤더 설정 수행함
        base_path = Path(__file__).resolve().parent.parent.parent
        csv_dir = os.path.join(base_path, "csv")

        if not os.path.exists(csv_dir):
            os.makedirs(csv_dir)
            print(f"데이터 저장 폴더 생성됨: {csv_dir}")

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"subject_{self.subject_index}_{self.group_id}_{timestamp_str}.csv"
        self.csv_path = os.path.join(csv_dir, filename)

        self.csv_file = open(self.csv_path, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.csv_file)

        header = [
            "timestamp",
            "delta",
            "theta",
            "alpha",
            "beta",
            "gamma",
            "focus",
            "engagement",
            "interest",
            "excitement",
            "stress",
            "relaxation",
        ]
        self.writer.writerow(header)

        # 4. 런타임 매핑, 상태 변수 및 버퍼 초기화 수행함
        self.met_map = {}
        self.eeg_channel_indices = []
        self.eeg_buffer = []
        self.latest_met = {
            "focus": 0,
            "engagement": 0,
            "interest": 0,
            "excitement": 0,
            "stress": 0,
            "relaxation": 0,
        }

        # 5. 필수 이벤트 바인딩 수행함
        self.bind(create_session_done=self.on_create_session_done)
        self.bind(new_data_labels=self.on_new_data_labels)
        self.bind(new_eeg_data=self.on_eeg_data_done)
        self.bind(new_met_data=self.on_new_met_data)
        self.bind(inform_error=self.on_inform_error)

        print(f"스트리밍 채널 활성화됨: {self.channel}")
        print(f"데이터 저장 경로: {self.csv_path}")

    def on_new_data_labels(self, *args, **kwargs):
        """MET 점수 및 EEG 채널 인덱스를 동적으로 매핑함"""
        data = kwargs.get("data")
        stream_name = data["streamName"]
        labels = data["labels"]

        if stream_name == "met":
            target_metrics = {
                "foc": "focus",
                "eng": "engagement",
                "int": "interest",
                "exc": "excitement",
                "str": "stress",
                "rel": "relaxation",
            }
            for label_key, met_key in target_metrics.items():
                if label_key in labels:
                    self.met_map[met_key] = labels.index(label_key)
            print(f"MET 인덱스 매핑 완료됨: {self.met_map}")

        elif stream_name == "eeg":
            target_eeg_channels = ["AF3", "T7", "Pz", "T8", "AF4"]
            self.eeg_channel_indices = [
                labels.index(ch) for ch in target_eeg_channels if ch in labels
            ]
            print(f"EEG 채널 인덱스 매핑 완료됨: {self.eeg_channel_indices}")

    def on_create_session_done(self, *args, **kwargs):
        print(f"세션 연결 성공하였음. {self.duration_min}분 측정을 시작함.")

        timer = threading.Timer(self.duration_sec, self.auto_stop)
        timer.daemon = True
        timer.start()

        self.sub_request(["eeg", "met"])

    def on_new_met_data(self, *args, **kwargs):
        """수신된 MET 배열에서 매핑된 점수 값만 추출함"""
        data = kwargs.get("data")["met"]
        for key, index in self.met_map.items():
            if index < len(data):
                self.latest_met[key] = data[index]

    def on_eeg_data_done(self, *args, **kwargs):
        """EEG 샘플을 버퍼링하고 1초(128샘플) 도달 시 대역 파워 계산 수행함"""
        data = kwargs.get("data")
        eeg_row = data["eeg"]
        cortex_time = data["time"]

        # 채널 인덱스가 아직 매핑되지 않은 경우 대기함
        if not self.eeg_channel_indices:
            return

        # 메타데이터를 제외한 순수 뇌파 채널 데이터만 추출하여 버퍼에 추가함
        channel_data = [eeg_row[i] for i in self.eeg_channel_indices]
        self.eeg_buffer.append(channel_data)

        # 버퍼에 1초 분량(128 샘플)의 데이터가 모였을 때 분석 실행함
        if len(self.eeg_buffer) >= self.analyzer.fs:
            # (128샘플 x 채널 수) 형태의 배열 생성함
            buffer_arr = np.array(self.eeg_buffer)

            # 공간(채널) 평균을 내어 1차원 시간 신호(길이 128)로 변환함
            mean_eeg_time_series = np.mean(buffer_arr, axis=1)

            # 시계열 데이터를 필터에 통과시켜 파워 대역 계산함
            powers = self.analyzer.get_all_powers(mean_eeg_time_series)

            # Cortex 타임스탬프를 문자열로 변환함
            formatted_time = datetime.fromtimestamp(cortex_time).strftime(
                "%Y-%m-%d %H:%M:%S.%f"
            )

            # 1. CSV 기록 수행함
            self.writer.writerow(
                [
                    formatted_time,
                    powers["delta"],
                    powers["theta"],
                    powers["alpha"],
                    powers["beta"],
                    powers["gamma"],
                    self.latest_met["focus"],
                    self.latest_met["engagement"],
                    self.latest_met["interest"],
                    self.latest_met["excitement"],
                    self.latest_met["stress"],
                    self.latest_met["relaxation"],
                ]
            )
            self.csv_file.flush()

            # 2. Redis 실시간 발행 수행함
            payload = {
                "type": "brain_sync_all",
                "groupId": self.group_id,
                "subjectIndex": self.subject_index,
                "waves": powers,
                "metrics": self.latest_met,
                "time": formatted_time,
            }
            self.r.publish(self.channel, json.dumps(payload))

            # 분석 완료 후 버퍼 초기화함 (비오버랩 방식)
            self.eeg_buffer = []

    def auto_stop(self):
        print(f"\n{self.duration_min}분이 경과하여 측정을 자동으로 종료함.")
        self.close()

    def on_inform_error(self, *args, **kwargs):
        error_data = kwargs.get("error_data")
        print(f"에러 발생함: {error_data}")
        self.close()  # 에러 발생 시 프로세스 정상 종료 보장함

    def on_close(self, *args, **kwargs):
        if hasattr(self, "csv_file") and not self.csv_file.closed:
            self.csv_file.close()
        print("프로그램이 안전하게 종료되었음.")
