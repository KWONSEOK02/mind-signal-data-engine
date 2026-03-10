import os
import sys

from dotenv import load_dotenv

from core.streamer import MindSignalStreamer

# 환경 변수 로드 수행함
load_dotenv(".env.local")


def main():
    """
    [Main] 명령어 인자를 통해 그룹 및 피실험자 정보를 주입받아 엔진 구동함
    """
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    # 인자 예외 처리 및 안내 문구 출력함
    if len(sys.argv) < 3:
        print("인자가 부족함. 사용법: python -m core.main <groupId> <subjectIndex>")
        sys.exit(1)

    if not client_id or not client_secret:
        print("환경 변수 파일에서 API 키를 확인해야 함.")
        sys.exit(1)

    group_id = sys.argv[1]
    subject_index = sys.argv[2]

    print(f"Mind Signal Engine 구동 시작함 (Group: {group_id}, Index: {subject_index})")

    # 스트리머 인스턴스 생성 및 실행 수행함
    streamer = MindSignalStreamer(group_id, subject_index, client_id, client_secret)
    streamer.open()


if __name__ == "__main__":
    main()
