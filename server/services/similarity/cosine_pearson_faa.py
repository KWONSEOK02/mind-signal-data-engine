import numpy as np

from ._base import SimilarityStrategy
from ._registry import register


@register
class CosinePearsonFAAStrategy(SimilarityStrategy):
    """코사인 유사도 + FAA 절대 차이 기반 반응 유사도 전략임"""

    name = "cosine_pearson_faa"

    def compute(self, a: dict, b: dict) -> dict:
        """스칼라 기반 input contract으로 유사도를 계산함.

        Input contract:
          a = {
            "waves_mean": {
                "delta": float, "theta": float, "alpha": float,
                "beta": float, "gamma": float
            },
            "faa_mean": float | None,
          }
          b = same

        Raises:
            ValueError: waves_mean에 필수 대역이 누락된 경우
            ValueError: waves_mean에 NaN 또는 Inf 값이 포함된 경우
        """
        band_order = ["delta", "theta", "alpha", "beta", "gamma"]

        # 0) 필수 대역 존재 여부 검증 수행함
        waves_a = a.get("waves_mean", {})
        waves_b = b.get("waves_mean", {})
        missing_a = [band for band in band_order if band not in waves_a]
        missing_b = [band for band in band_order if band not in waves_b]
        if missing_a or missing_b:
            raise ValueError(
                f"Missing bands in waves_mean: "
                f"subject_a={missing_a}, subject_b={missing_b}. "
                f"Expected all of {band_order}."
            )

        # 1) 대역별 5-요소 벡터 구성 수행함
        vec_a = np.array([waves_a[band] for band in band_order], dtype=float)
        vec_b = np.array([waves_b[band] for band in band_order], dtype=float)

        # NaN/Inf 방어 검증 수행함
        if np.any(np.isnan(vec_a)) or np.any(np.isnan(vec_b)):
            raise ValueError(
                "NaN detected in waves_mean — "
                "likely data quality issue (empty session or filter divergence)"
            )
        if np.any(np.isinf(vec_a)) or np.any(np.isinf(vec_b)):
            raise ValueError("Inf detected in waves_mean — likely filter divergence")

        # 영벡터 방어 처리 — 진짜 빈 데이터와 직교를 구별함
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a < 1e-12 or norm_b < 1e-12:
            return {
                "algorithm": self.name,
                "similarity_score": None,
                "overall_cosine": None,
                "band_ratio_diff": {band: 0.0 for band in band_order},
                "faa_absolute_diff": None,
                "degraded": True,
                "degraded_reason": "zero_norm",
            }

        # 2) 코사인 유사도 계산 수행함
        overall_cosine = self._cosine(vec_a, vec_b)

        # 개별 대역 파워 절대 차이 계산함 (추가 진단 정보)
        band_ratio_diff = {
            band: abs(waves_a[band] - waves_b[band]) for band in band_order
        }

        # 3) FAA 절대 차이 계산함 (scalar 차이, 시계열 없으므로 피어슨 상관 제외)
        faa_diff = None
        if a.get("faa_mean") is not None and b.get("faa_mean") is not None:
            faa_diff = abs(a["faa_mean"] - b["faa_mean"])

        # 4) overall similarity_score 정규화 (0~1 범위)
        similarity_score = self._normalize(overall_cosine, faa_diff)

        return {
            "algorithm": self.name,
            "similarity_score": similarity_score,
            "overall_cosine": overall_cosine,
            "band_ratio_diff": band_ratio_diff,
            "faa_absolute_diff": faa_diff,
        }

    def _cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        """두 벡터의 코사인 유사도를 계산함"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

    def _normalize(self, cosine: float, faa_diff: float | None) -> float:
        """cosine 유사도를 0~1로 정규화하고 FAA 차이 감점을 적용함.

        대역 파워는 음수가 없으므로 cosine ∈ [0, 1]. (cosine+1)/2 매핑은
        직교(cosine=0)를 0.5로 올려 의미가 왜곡되므로 직접 사용함.
        FAA 차이가 클수록 유사도 감소 (단순 선형 감점, 교수 면담 후 가중치 조정 가능).
        """
        # 대역 파워는 비음수 → cosine ∈ [0, 1]. 직접 clamp 적용함
        score = max(0.0, cosine)

        # FAA 차이 클수록 유사도 감소 (faa_diff 2 이상 시 최대 50% 감점)
        if faa_diff is not None:
            score *= max(0.0, 1.0 - min(faa_diff / 2.0, 0.5))

        return float(max(0.0, min(1.0, score)))
