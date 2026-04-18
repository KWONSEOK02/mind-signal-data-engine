"""similarity Strategy Pattern 패키지 단위 테스트 수행함"""

import pytest


class TestRegistry:
    def test_registry_contains_cosine_pearson_faa_after_import(self):
        """import 후 REGISTRY에 'cosine_pearson_faa' 키 존재함"""
        from server.services.similarity import REGISTRY

        assert "cosine_pearson_faa" in REGISTRY

    def test_unknown_algorithm_raises_value_error(self):
        """존재하지 않는 알고리즘 이름 → ValueError 발생함"""
        from server.services.similarity import compute

        a = {
            "waves_mean": {
                "delta": 1.0,
                "theta": 0.0,
                "alpha": 0.0,
                "beta": 0.0,
                "gamma": 0.0,
            },
            "faa_mean": None,
        }
        with pytest.raises(ValueError, match="Unknown similarity strategy"):
            compute(a, a, algorithm="nonexistent_algo")


class TestCosinePearsonFAAStrategy:
    """CosinePearsonFAAStrategy.compute 검증함"""

    @pytest.fixture
    def identical_subject(self):
        """동일한 waves_mean + faa_mean=None 피실험자 데이터 반환함"""
        return {
            "waves_mean": {
                "delta": 0.5,
                "theta": 0.3,
                "alpha": 0.8,
                "beta": 0.4,
                "gamma": 0.2,
            },
            "faa_mean": None,
        }

    @pytest.fixture
    def alpha_only_subject(self):
        """alpha=1.0, 나머지=0.0인 피실험자 데이터 반환함"""
        return {
            "waves_mean": {
                "delta": 0.0,
                "theta": 0.0,
                "alpha": 1.0,
                "beta": 0.0,
                "gamma": 0.0,
            },
            "faa_mean": None,
        }

    @pytest.fixture
    def beta_only_subject(self):
        """beta=1.0, 나머지=0.0인 피실험자 데이터 반환함"""
        return {
            "waves_mean": {
                "delta": 0.0,
                "theta": 0.0,
                "alpha": 0.0,
                "beta": 1.0,
                "gamma": 0.0,
            },
            "faa_mean": None,
        }

    def test_identical_inputs_similarity_score_near_one(self, identical_subject):
        """동일 입력 → similarity_score가 1.0에 매우 가까움"""
        from server.services.similarity import compute

        result = compute(identical_subject, identical_subject)
        assert result["similarity_score"] >= 0.95

    def test_orthogonal_vectors_overall_cosine_zero(
        self, alpha_only_subject, beta_only_subject
    ):
        """직교 벡터 (alpha전용 vs beta전용) → overall_cosine == 0.0"""
        from server.services.similarity import compute

        result = compute(alpha_only_subject, beta_only_subject)
        assert abs(result["overall_cosine"]) < 1e-9

    def test_faa_mean_none_both_returns_dict_without_key_error(self, identical_subject):
        """faa_mean=None 양측 → KeyError 없이 dict 반환, faa_absolute_diff is None"""
        from server.services.similarity import compute

        result = compute(identical_subject, identical_subject)
        assert isinstance(result, dict)
        assert result["faa_absolute_diff"] is None

    def test_return_keys_complete(self, identical_subject):
        """반환 dict에 필수 키 5개 모두 존재함"""
        from server.services.similarity import compute

        result = compute(identical_subject, identical_subject)
        required_keys = {
            "algorithm",
            "similarity_score",
            "overall_cosine",
            "band_ratio_diff",
            "faa_absolute_diff",
        }
        assert required_keys == set(result.keys())

    def test_algorithm_field_value(self, identical_subject):
        """algorithm 필드 값이 'cosine_pearson_faa'임"""
        from server.services.similarity import compute

        result = compute(identical_subject, identical_subject)
        assert result["algorithm"] == "cosine_pearson_faa"

    def test_similarity_score_range_zero_to_one(
        self, alpha_only_subject, beta_only_subject
    ):
        """similarity_score는 항상 0~1 범위임"""
        from server.services.similarity import compute

        result = compute(alpha_only_subject, beta_only_subject)
        assert 0.0 <= result["similarity_score"] <= 1.0

    def test_faa_mean_provided_both_computes_absolute_diff(self):
        """faa_mean 양측 모두 제공 시 faa_absolute_diff = abs(a - b)"""
        from server.services.similarity import compute

        a = {
            "waves_mean": {
                "delta": 0.5,
                "theta": 0.3,
                "alpha": 0.8,
                "beta": 0.4,
                "gamma": 0.2,
            },
            "faa_mean": 1.5,
        }
        b = {
            "waves_mean": {
                "delta": 0.5,
                "theta": 0.3,
                "alpha": 0.8,
                "beta": 0.4,
                "gamma": 0.2,
            },
            "faa_mean": 0.5,
        }
        result = compute(a, b)
        assert abs(result["faa_absolute_diff"] - 1.0) < 1e-9

    def test_band_ratio_diff_has_five_bands(self, identical_subject):
        """band_ratio_diff dict에 5개 대역 키 존재함"""
        from server.services.similarity import compute

        result = compute(identical_subject, identical_subject)
        expected_bands = {"delta", "theta", "alpha", "beta", "gamma"}
        assert set(result["band_ratio_diff"].keys()) == expected_bands

    def test_missing_band_raises_value_error(self):
        """waves_mean에 대역 누락 시 ValueError 발생함"""
        from server.services.similarity import compute

        a = {
            "waves_mean": {
                "delta": 0.5,
                "theta": 0.3,
                # alpha 누락
                "beta": 0.4,
                "gamma": 0.2,
            },
            "faa_mean": None,
        }
        b = {
            "waves_mean": {
                "delta": 0.5,
                "theta": 0.3,
                "alpha": 0.8,
                "beta": 0.4,
                "gamma": 0.2,
            },
            "faa_mean": None,
        }
        with pytest.raises(ValueError, match="Missing bands in waves_mean"):
            compute(a, b)

    def test_nan_in_waves_mean_raises_value_error(self):
        """waves_mean에 NaN 포함 시 ValueError 발생함"""
        from server.services.similarity import compute

        a = {
            "waves_mean": {
                "delta": float("nan"),
                "theta": 0.3,
                "alpha": 0.8,
                "beta": 0.4,
                "gamma": 0.2,
            },
            "faa_mean": None,
        }
        b = {
            "waves_mean": {
                "delta": 0.5,
                "theta": 0.3,
                "alpha": 0.8,
                "beta": 0.4,
                "gamma": 0.2,
            },
            "faa_mean": None,
        }
        with pytest.raises(ValueError, match="NaN detected in waves_mean"):
            compute(a, b)

    def test_inf_in_waves_mean_raises_value_error(self):
        """waves_mean에 Inf 포함 시 ValueError 발생함"""
        from server.services.similarity import compute

        a = {
            "waves_mean": {
                "delta": float("inf"),
                "theta": 0.3,
                "alpha": 0.8,
                "beta": 0.4,
                "gamma": 0.2,
            },
            "faa_mean": None,
        }
        b = {
            "waves_mean": {
                "delta": 0.5,
                "theta": 0.3,
                "alpha": 0.8,
                "beta": 0.4,
                "gamma": 0.2,
            },
            "faa_mean": None,
        }
        with pytest.raises(ValueError, match="Inf detected in waves_mean"):
            compute(a, b)

    def test_zero_vector_returns_none_similarity_score_and_degraded(self):
        """모든 대역=0인 영벡터 → similarity_score=None + degraded=True 반환함"""
        from server.services.similarity import compute

        zero_subject = {
            "waves_mean": {
                "delta": 0.0,
                "theta": 0.0,
                "alpha": 0.0,
                "beta": 0.0,
                "gamma": 0.0,
            },
            "faa_mean": None,
        }
        normal_subject = {
            "waves_mean": {
                "delta": 0.5,
                "theta": 0.3,
                "alpha": 0.8,
                "beta": 0.4,
                "gamma": 0.2,
            },
            "faa_mean": None,
        }
        result = compute(zero_subject, normal_subject)
        assert result["similarity_score"] is None
        assert result["degraded"] is True
        assert result["degraded_reason"] == "zero_norm"

    def test_orthogonal_score_zero_not_half(
        self, alpha_only_subject, beta_only_subject
    ):
        """직교 벡터 → similarity_score=0.0 (이전 (cosine+1)/2 매핑의 0.5 아님)"""
        from server.services.similarity import compute

        result = compute(alpha_only_subject, beta_only_subject)
        assert abs(result["similarity_score"]) < 1e-9

    def test_identical_vectors_score_near_one_with_new_normalize(
        self, identical_subject
    ):
        """동일 벡터 → max(0, cosine) 매핑에서도 similarity_score ≈ 1.0"""
        from server.services.similarity import compute

        result = compute(identical_subject, identical_subject)
        assert result["similarity_score"] >= 0.95
