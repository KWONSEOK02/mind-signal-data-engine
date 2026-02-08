import os
import json
import redis
from sdk.cortex import Cortex
from core.analyzer import MindSignalAnalyzer  # 분석기 불러오기
from dotenv import load_dotenv

load_dotenv('.env.local')

class MindSignalStreamer(Cortex):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 환경변수에서 Redis 정보를 가져오도록 수정
        self.r = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0))
        )
        self.channel = os.getenv('REDIS_CHANNEL', 'mind-signal-live')

    def on_create_session_done(self, *args, **kwargs):
        print("🚀 세션 연결 성공! 실시간 스트리밍을 시작합니다.")
        self.sub_request(['eeg', 'met'])

    def on_new_eeg_data(self, *args, **kwargs):
        data = kwargs.get('data')
        eeg_values = data['eeg'] # 채널 데이터 추출
        
        # 실시간 분석: 알파파와 베타파 추출
        alpha_wave = self.analyzer.filter_alpha(eeg_values)
        beta_wave = self.analyzer.filter_beta(eeg_values)
        
        # Redis로 가공된 데이터 전송 (프론트엔드 시각화용)
        payload = {
            'type': 'eeg_processed',
            'raw': eeg_values,
            'alpha': alpha_wave.tolist(),
            'beta': beta_wave.tolist(),
            'time': data['time']
        }
        self.r.publish(self.channel, json.dumps(payload))

    def on_inform_error(self, *args, **kwargs):
        error_data = kwargs.get('error_data')
        print(f"❌ 에러 발생: {error_data}")

# --- 실제 엔진 가동부 ---
if __name__ == "__main__":
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("❌ .env.local 파일에서 API 키를 확인하세요.")
    else:
        streamer = MindSignalStreamer(client_id, client_secret, debug_mode=False)
        streamer.open()