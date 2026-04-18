"""SEQUENTIAL 파이프라인 및 similarity 엣지 케이스 통합 테스트 수행함"""

import numpy as np
import pandas as pd
import pytest

from pathlib import Path
from unittest.mock import patch

from tests.conftest import TEST_GROUP_ID


# ──────────────────────────────────────────────
# Fixture
# ──────────────────────────────────────────────


@pytest.fixture
def identical_waves_df():
    """두 피실험자가 동일한 뇌파 패턴을 보이는 60행 DataFrame 반환함"""
    np.random.seed(42)
    n = 60
    base_data = {
        "delta": np.full(n, 0.5),
        "theta": np.full(n, 0.3),
        "alpha": np.full(n, 0.8),
        "beta": np.full(n, 0.4),
        "gamma": np.full(n, 0.2),
        "focus": np.full(n, 0.5),
        "engagement": np.full(n, 0.5),
        "interest": np.full(n, 0.5),
        "excitement": np.full(n, 0.5),
        "stress": np.full(n, 0.5),
        "relaxation": np.full(n, 0.5),
    }
    return pd.DataFrame(base_data)


# ──────────────────────────────────────────────
# TestSequentialIntegration
# ──────────────────────────────────────────────


class TestSequentialIntegration:
    """route → service → similarity 전체 경로 통합 검증 수행함"""

    def test_unknown_algorithm_via_pipeline_raises_value_error(
        self, test_client, pipeline_secret_header, identical_waves_df
    ):
        """알 수 없는 algorithm → ValueError 발생함 (서비스 레이어 검증)"""
        with patch(
            "server.services.analysis.find_csv_files",
            lambda group_id, subject_index: [
                Path(f"/fake/subject_{subject_index}_{group_id}.csv")
            ],
        ), patch(
            "server.services.analysis.load_session_data",
            lambda path: identical_waves_df.copy(),
        ):
            # TestClient는 기본적으로 서버 예외를 그대로 re-raise함
            # ValueError를 직접 확인함
            with pytest.raises(ValueError, match="Unknown similarity strategy"):
                test_client.post(
                    "/api/analyze/pipeline",
                    json={
                        "group_id": TEST_GROUP_ID,
                        "subject_indices": [1, 2],
                        "mode": "SEQUENTIAL",
                        "algorithm": "nonexistent_algo_xyz",
                    },
                    headers=pipeline_secret_header,
                )

    def test_sequential_identical_waves_similarity_score_near_one(
        self, test_client, pipeline_secret_header, identical_waves_df
    ):
        """동일 뇌파 패턴 두 피실험자 → similarity_score ≥ 0.95 (통합 경로)"""
        with patch(
            "server.services.analysis.find_csv_files",
            lambda group_id, subject_index: [
                Path(f"/fake/subject_{subject_index}_{group_id}.csv")
            ],
        ), patch(
            "server.services.analysis.load_session_data",
            lambda path: identical_waves_df.copy(),
        ):
            response = test_client.post(
                "/api/analyze/pipeline",
                json={
                    "group_id": TEST_GROUP_ID,
                    "subject_indices": [1, 2],
                    "mode": "SEQUENTIAL",
                },
                headers=pipeline_secret_header,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["similarity_features"] is not None
            assert data["similarity_features"]["similarity_score"] >= 0.95

    def test_sequential_response_pair_features_is_none(
        self, test_client, pipeline_secret_header, identical_waves_df
    ):
        """SEQUENTIAL 모드 route 응답 → pair_features=None (DUAL 전용 필드)"""
        with patch(
            "server.services.analysis.find_csv_files",
            lambda group_id, subject_index: [
                Path(f"/fake/subject_{subject_index}_{group_id}.csv")
            ],
        ), patch(
            "server.services.analysis.load_session_data",
            lambda path: identical_waves_df.copy(),
        ):
            response = test_client.post(
                "/api/analyze/pipeline",
                json={
                    "group_id": TEST_GROUP_ID,
                    "subject_indices": [1, 2],
                    "mode": "SEQUENTIAL",
                },
                headers=pipeline_secret_header,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["pair_features"] is None
            assert data["y_score"] is None
            assert data["synchrony_score"] is None

    def test_dual_regression_via_route_similarity_features_none(
        self, test_client, pipeline_secret_header, valid_pipeline_result
    ):
        """DUAL 모드 route 응답 → similarity_features=None (SEQUENTIAL 전용 필드)"""
        with patch("server.services.analysis.run_full_pipeline") as mock_pipeline:
            mock_pipeline.return_value = valid_pipeline_result
            response = test_client.post(
                "/api/analyze/pipeline",
                json={
                    "group_id": TEST_GROUP_ID,
                    "subject_indices": [1, 2],
                    "mode": "DUAL",
                },
                headers=pipeline_secret_header,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["similarity_features"] is None
