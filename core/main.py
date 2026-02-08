from sdk.cortex import Cortex
import os
from dotenv import load_dotenv

load_dotenv()

class MindSignalEngine(Cortex):
    def on_create_session_done(self, *args, **kwargs):
        print("🚀 세션 연결 완료! 이제 데이터를 받을 수 있습니다.")

# 실행부
engine = MindSignalEngine(os.getenv("CLIENT_ID"), os.getenv("CLIENT_SECRET"))
engine.open()