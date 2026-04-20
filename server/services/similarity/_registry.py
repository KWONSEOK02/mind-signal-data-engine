from typing import Type

from ._base import SimilarityStrategy

REGISTRY: dict[str, Type[SimilarityStrategy]] = {}


def register(
    strategy_cls: Type[SimilarityStrategy],
) -> Type[SimilarityStrategy]:
    """Decorator: @register on new strategy class auto-registers it."""
    REGISTRY[strategy_cls.name] = strategy_cls
    return strategy_cls


def get(name: str = "default") -> SimilarityStrategy:
    """이름으로 전략 인스턴스를 반환함"""
    if name == "default":
        name = "cosine_pearson_faa"
    if name not in REGISTRY:
        raise ValueError(
            f"Unknown similarity strategy: {name}. Available: {list(REGISTRY.keys())}"
        )
    return REGISTRY[name]()
