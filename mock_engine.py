import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


# 분석 엔진 역할을 수행하는 Mock 서버 클래스임
class MockAnalyzerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 요청 경로가 /api/analyzer/로 시작하는지 확인함
        if self.path.startswith("/api/analyzer/"):
            # 타임아웃(AbortController) 테스트가 필요한 경우 아래 주석을 해제함
            # time.sleep(6) # 6초 지연을 발생시켜 408 에러 유도함

            # 경로에서 userId를 추출함
            user_id = self.path.split("/")[-1]

            # 성공 응답 헤더를 설정함
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            # 반환할 더미 데이터 정의함
            response_data = {
                "status": "success",
                "userId": user_id,
                "analysis": {
                    "score": 85,
                    "comment": "집중도가 높은 상태이며 뇌파 시그널이 안정적임",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }

            # JSON 형식으로 변환하여 응답함
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
        else:
            # 정의되지 않은 경로 요청 시 404 에러 반환함
            self.send_response(404)
            self.end_headers()


# 서버 실행 함수임
def run_mock_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, MockAnalyzerHandler)
    print(f"Mock 데이터 엔진이 http://localhost:{port} 에서 구동 중임")
    print("종료하려면 Ctrl+C를 누름")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료함")
        httpd.server_close()


if __name__ == "__main__":
    # .env.local의 DATA_ENGINE_BASE_URL 포트와 일치시킴
    run_mock_server(8000)
