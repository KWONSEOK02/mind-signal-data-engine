from . import cosine_pearson_faa  # noqa: F401 — 등록 트리거
from ._registry import REGISTRY, get


def compute(
    subject_a: dict,
    subject_b: dict,
    algorithm: str = "default",
) -> dict:
    """외부에서 호출하는 단일 entry point임."""
    strategy = get(algorithm)
    return strategy.compute(subject_a, subject_b)


__all__ = ["compute", "REGISTRY"]
