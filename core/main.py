import os

from dotenv import load_dotenv

from sdk.cortex import Cortex

load_dotenv(".env.local")


class MindSignalEngine(Cortex):
    def on_create_session_done(self, *args, **kwargs):
        print("🚀 세션 연결 완료! 이제 데이터를 받을 수 있습니다.")


# 실행부
engine = MindSignalEngine(os.getenv("CLIENT_ID"), os.getenv("CLIENT_SECRET"))
engine.open()
