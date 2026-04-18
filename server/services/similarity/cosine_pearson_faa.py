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
        """
        # 1) 대역별 5-요소 벡터의 코사인 유사도 계산함
        band_order = ["delta", "theta", "alpha", "beta", "gamma"]
        vec_a = np.array([a["waves_mean"][band] for band in band_order])
        vec_b = np.array([b["waves_mean"][band] for band in band_order])
        overall_cosine = self._cosine(vec_a, vec_b)

        # 개별 대역 파워 절대 차이 계산함 (추가 진단 정보)
        band_ratio_diff = {
            band: abs(a["waves_mean"][band] - b["waves_mean"][band])
            for band in band_order
        }

        # 2) FAA 절대 차이 계산함 (scalar 차이, 시계열 없으므로 피어슨 상관 제외)
        faa_diff = None
        if a.get("faa_mean") is not None and b.get("faa_mean") is not None:
            faa_diff = abs(a["faa_mean"] - b["faa_mean"])

        # 3) overall similarity_score 정규화 (0~1 범위)
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
        return float(
            np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)
        )

    def _normalize(self, cosine: float, faa_diff: float | None) -> float:
        """cosine 유사도를 0~1로 정규화하고 FAA 차이 감점을 적용함.

        FAA 차이가 클수록 유사도 감소 (단순 선형 감점, 교수 면담 후 가중치 조정 가능).
        """
        # cosine은 -1~1 범위. 0~1로 정규화함
        score = (cosine + 1) / 2

        # FAA 차이 클수록 유사도 감소 (faa_diff 2 이상 시 최대 50% 감점)
        if faa_diff is not None:
            score *= max(0.0, 1.0 - min(faa_diff / 2.0, 0.5))

        return float(max(0.0, min(1.0, score)))
