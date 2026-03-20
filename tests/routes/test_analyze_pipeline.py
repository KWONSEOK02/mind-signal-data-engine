"""POST /api/analyze/pipeline 엔드포인트 테스트"""

from unittest.mock import patch

import pytest

from tests.conftest import TEST_GROUP_ID, TEST_SECRET


class TestAnalyzePipelineEndpoint:
    """POST /api/analyze/pipeline 엔드포인트 검증함"""

    def test_missing_secret_header_returns_422(self, test_client):
        """Header 미제공 시 FastAPI validation error (422) 반환함"""
        response = test_client.post(
            "/api/analyze/pipeline",
            json={"group_id": TEST_GROUP_ID, "subject_indices": [1, 2]},
            # X-Engine-Secret 헤더 미포함
        )
        assert response.status_code == 422

    def test_wrong_secret_returns_403(self, test_client):
        """잘못된 secret → 403 반환함"""
        response = test_client.post(
            "/api/analyze/pipeline",
            json={"group_id": TEST_GROUP_ID, "subject_indices": [1, 2]},
            headers={"X-Engine-Secret": "wrong-secret"},
        )
        assert response.status_code == 403

    @patch("server.services.analysis.run_full_pipeline")
    def test_valid_request_returns_200(self, mock_pipeline, test_client, pipeline_secret_header, valid_pipeline_result):
        """올바른 요청 → 200 반환함"""
        mock_pipeline.return_value = valid_pipeline_result
        response = test_client.post(
            "/api/analyze/pipeline",
            json={"group_id": TEST_GROUP_ID, "subject_indices": [1, 2]},
            headers=pipeline_secret_header,
        )
        assert response.status_code == 200

    @patch("server.services.analysis.run_full_pipeline")
    def test_response_group_id_matches(self, mock_pipeline, test_client, pipeline_secret_header, valid_pipeline_result):
        """응답 JSON의 group_id가 요청과 일치함"""
        mock_pipeline.return_value = valid_pipeline_result
        response = test_client.post(
            "/api/analyze/pipeline",
            json={"group_id": TEST_GROUP_ID, "subject_indices": [1, 2]},
            headers=pipeline_secret_header,
        )
        data = response.json()
        assert data["group_id"] == TEST_GROUP_ID

    @patch("server.services.analysis.run_full_pipeline")
    def test_response_has_pipeline_params(self, mock_pipeline, test_client, pipeline_secret_header, valid_pipeline_result):
        """응답 pipeline_params에 필수 키 존재함"""
        mock_pipeline.return_value = valid_pipeline_result
        response = test_client.post(
            "/api/analyze/pipeline",
            json={"group_id": TEST_GROUP_ID, "subject_indices": [1, 2]},
            headers=pipeline_secret_header,
        )
        data = response.json()
        assert "pipeline_params" in data
        assert "stimulus_duration_sec" in data["pipeline_params"]

    @patch("server.services.analysis.run_full_pipeline")
    def test_include_markdown_true(self, mock_pipeline, test_client, pipeline_secret_header, valid_pipeline_result):
        """include_markdown=true 시 markdown 필드가 None이 아님"""
        # features_to_markdown이 호출되려면 subjects에 features가 있어야 함
        mock_pipeline.return_value = valid_pipeline_result
        response = test_client.post(
            "/api/analyze/pipeline",
            json={
                "group_id": TEST_GROUP_ID,
                "subject_indices": [1, 2],
                "include_markdown": True,
            },
            headers=pipeline_secret_header,
        )
        data = response.json()
        assert data["markdown"] is not None

    @patch("server.services.analysis.run_full_pipeline")
    def test_include_markdown_false(self, mock_pipeline, test_client, pipeline_secret_header, valid_pipeline_result):
        """include_markdown=false(기본값) 시 markdown=None임"""
        mock_pipeline.return_value = valid_pipeline_result
        response = test_client.post(
            "/api/analyze/pipeline",
            json={"group_id": TEST_GROUP_ID, "subject_indices": [1, 2]},
            headers=pipeline_secret_header,
        )
        data = response.json()
        assert data["markdown"] is None

    @patch("server.services.analysis.run_full_pipeline")
    def test_satisfaction_scores_returns_y_score(self, mock_pipeline, test_client, pipeline_secret_header, valid_pipeline_result):
        """satisfaction_scores 포함 요청 시 y_score가 None이 아님"""
        mock_pipeline.return_value = valid_pipeline_result
        response = test_client.post(
            "/api/analyze/pipeline",
            json={
                "group_id": TEST_GROUP_ID,
                "subject_indices": [1, 2],
                "satisfaction_scores": {"1": 7.5, "2": 6.0},
            },
            headers=pipeline_secret_header,
        )
        data = response.json()
        assert data["y_score"] is not None

    @patch("server.services.analysis.run_full_pipeline")
    def test_csv_not_found_in_response(self, mock_pipeline, test_client, pipeline_secret_header):
        """CSV 없는 subject의 응답 처리 검증함"""
        # subjects에 error가 없는 정상 응답을 반환하되, 최소 구조만 갖춤
        mock_pipeline.return_value = {
            "group_id": TEST_GROUP_ID,
            "subjects": [
                {
                    "subject_index": 1,
                    "baseline": {"alpha": 0.5},
                    "features": {},
                    "n_features": 0,
                }
            ],
            "pair_features": None,
            "y_score": None,
            "synchrony_score": None,
            "pipeline_params": {
                "stimulus_duration_sec": 60,
                "window_size_sec": 10,
                "n_stimuli": 10,
                "baseline_duration_sec": 30,
                "band_cols": ["alpha"],
                "n_windows_per_stimulus": 6,
                "total_features_per_subject": 0,
            },
            "dataframes": {},
        }
        response = test_client.post(
            "/api/analyze/pipeline",
            json={"group_id": TEST_GROUP_ID, "subject_indices": [1]},
            headers=pipeline_secret_header,
        )
        assert response.status_code == 200

    def test_invalid_body_missing_group_id(self, test_client, pipeline_secret_header):
        """group_id 미포함 body → 422 validation error 반환함"""
        response = test_client.post(
            "/api/analyze/pipeline",
            json={"subject_indices": [1, 2]},  # group_id 누락
            headers=pipeline_secret_header,
        )
        assert response.status_code == 422
