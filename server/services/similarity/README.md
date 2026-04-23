# Similarity Strategies

## 새 알고리즘 추가 방법 (논문 읽고 수식 업데이트 시)

1. `similarity/<your_strategy_name>.py` 파일 생성
2. `SimilarityStrategy` 상속 + `name` 설정 + `compute(a, b)` 구현
3. `@register` 데코레이터 추가
4. `__init__.py`에 `from . import <your_strategy_name>` 한 줄 추가
5. `/api/analyze/pipeline` 요청 시 body에 `"algorithm": "<your_strategy_name>"` 전달

기존 `cosine_pearson_faa` 코드 변경 없음. DB 스키마 변경 없음 (JSONB 저장).

---

## Strategy (mode) 비교

| mode | 입력 | 출력 | 활용 시점 |
|------|------|------|----------|
| **SEQUENTIAL** | 시분할 측정 2개 CSV (피실험자 각각 별도 녹화) | `similarity_features` (유사도 수치) | 헤드셋 1대로 피실험자를 순차 측정할 때 |
| **DUAL** | 동시 측정 2개 CSV (동기화됨) | `subjects`, `pair_features`, `y_score`, `synchrony_score` | 헤드셋 2대로 피실험자를 동시 측정할 때 (단일 DE) |
| **BTI** | 동시 측정 2개 CSV (동기화됨) | DUAL과 동일 구조 | BTI(Brain-To-Interface) 실험 — 자극 반응 타이밍 분석 포함 |
| **DUAL_2PC** | 2PC에서 수집한 동기화된 CSV (피실험자별 DE에서 각각 업로드) | DUAL과 동일 구조 + `similarity_features: {"mode": "DUAL_2PC"}` | 헤드셋 2대 + DE 2대 2PC 구성에서 두 subject 데이터를 동일 파이프라인으로 분석 |

> DUAL_2PC는 신규 similarity 파일 불필요 — `cosine_pearson_faa.compute(a, b)` 재활용.
> BE가 subject 1 담당 DE를 analysis 전담으로 지정하고 `subject_indices=[1, 2]`를 전달함 (Phase 16 Wave 1).
