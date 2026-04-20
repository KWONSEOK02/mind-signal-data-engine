from abc import ABC, abstractmethod


class SimilarityStrategy(ABC):
    """Similarity 계산 전략의 ABC. 새 논문/수식 추가 시 이 클래스를 상속해 구현."""

    name: str  # registry key (e.g. "cosine_pearson_faa", "lstm_based_2026")

    @abstractmethod
    def compute(self, subject_a_data: dict, subject_b_data: dict) -> dict:
        """Return similarity features dict (shape is strategy-specific)."""
