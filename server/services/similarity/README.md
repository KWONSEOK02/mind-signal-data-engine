# Similarity Strategies

## 새 알고리즘 추가 방법 (논문 읽고 수식 업데이트 시)

1. `similarity/<your_strategy_name>.py` 파일 생성
2. `SimilarityStrategy` 상속 + `name` 설정 + `compute(a, b)` 구현
3. `@register` 데코레이터 추가
4. `__init__.py`에 `from . import <your_strategy_name>` 한 줄 추가
5. `/api/analyze/pipeline` 요청 시 body에 `"algorithm": "<your_strategy_name>"` 전달

기존 `cosine_pearson_faa` 코드 변경 없음. DB 스키마 변경 없음 (JSONB 저장).
