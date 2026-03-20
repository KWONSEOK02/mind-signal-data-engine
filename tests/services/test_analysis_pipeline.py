"""analysis 서비스 파이프라인 단계별 단위/통합 테스트 수행함"""

from collections import OrderedDict
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from tests.conftest import (
    DEFAULT_BAND_COLS,
    TEST_GROUP_ID,
)
from server.services.analysis import (
    average_by_timestamp,
    build_pair_features,
    compute_baseline,
    compute_y,
    extract_features,
    run_full_pipeline,
    split_stimulus_windows,
)


# ──────────────────────────────────────────────
# TestAverageByTimestamp
# ──────────────────────────────────────────────


class TestAverageByTimestamp:
    def test_no_time_col_returns_band_cols_only(self, simple_df, band_cols):
        """time/timestamp 컬럼 없는 DataFrame → 반환 컬럼이 band_cols와 일치함"""
        result = average_by_timestamp(simple_df, band_cols)
        assert list(result.columns) == band_cols

    def test_no_time_col_preserves_row_count(self, simple_df, band_cols):
        """time 컬럼 없으면 행 수 변화 없음"""
        result = average_by_timestamp(simple_df, band_cols)
        assert len(result) == len(simple_df)

    def test_no_time_col_index_reset(self, simple_df, band_cols):
        """반환 DataFrame의 index가 0부터 연속 정수임"""
        result = average_by_timestamp(simple_df, band_cols)
        assert list(result.index) == list(range(len(result)))

    def test_timestamp_col_groups_and_averages(self, timestamped_df, band_cols):
        """timestamp 컬럼 존재 시 동일 timestamp의 값이 평균화되어 행 수 감소함"""
        result = average_by_timestamp(timestamped_df, band_cols)
        # 30개 unique timestamp → 30행으로 축소
        assert len(result) == 30

    def test_time_col_preferred_over_timestamp(self, band_cols):
        """'time'과 'timestamp' 동시 존재 시 'time' 우선 사용함"""
        np.random.seed(42)
        df = pd.DataFrame({
            "time": [0, 0, 1, 1],
            "timestamp": [10, 10, 20, 20],
            "alpha": [1.0, 3.0, 2.0, 4.0],
            "beta": [0.5, 0.5, 1.5, 1.5],
            "theta": [0.1, 0.3, 0.2, 0.4],
            "gamma": [0.2, 0.4, 0.3, 0.5],
        })
        result = average_by_timestamp(df, band_cols)
        # 'time' 기준 2개 그룹 → 2행
        assert len(result) == 2

    def test_partial_band_cols_in_df(self):
        """DataFrame에 band_cols 일부만 존재할 때 존재하는 것만 반환함"""
        df = pd.DataFrame({"alpha": [1.0, 2.0], "beta": [3.0, 4.0]})
        result = average_by_timestamp(df, ["alpha", "beta", "nonexistent"])
        assert "nonexistent" not in result.columns
        assert "alpha" in result.columns
        assert "beta" in result.columns


# ──────────────────────────────────────────────
# TestComputeBaseline
# ──────────────────────────────────────────────


class TestComputeBaseline:
    def test_returns_dict_with_all_bands(self, simple_df, band_cols):
        """반환 dict의 키가 band_cols와 일치함"""
        result = compute_baseline(simple_df, band_cols)
        assert set(result.keys()) == set(band_cols)

    def test_mean_of_first_n_rows(self, simple_df, band_cols):
        """값이 실제 첫 30행의 평균과 일치함"""
        result = compute_baseline(simple_df, band_cols, baseline_duration_sec=30)
        expected_alpha = float(simple_df["alpha"].iloc[:30].mean())
        assert abs(result["alpha"] - expected_alpha) < 1e-10

    def test_custom_baseline_duration(self, simple_df, band_cols):
        """baseline_duration_sec=10 지정 시 첫 10행 기준 평균 사용함"""
        result = compute_baseline(simple_df, band_cols, baseline_duration_sec=10)
        expected = float(simple_df["alpha"].iloc[:10].mean())
        assert abs(result["alpha"] - expected) < 1e-10

    def test_missing_band_col_excluded(self):
        """DataFrame에 없는 band 컬럼은 결과 dict에서 제외됨"""
        df = pd.DataFrame({"alpha": [1.0, 2.0, 3.0]})
        result = compute_baseline(df, ["alpha", "nonexistent"], baseline_duration_sec=3)
        assert "alpha" in result
        assert "nonexistent" not in result

    def test_values_are_float(self, simple_df, band_cols):
        """반환 dict의 모든 value가 float 타입임"""
        result = compute_baseline(simple_df, band_cols)
        for val in result.values():
            assert isinstance(val, float)


# ──────────────────────────────────────────────
# TestSplitStimulusWindows
# ──────────────────────────────────────────────


class TestSplitStimulusWindows:
    def test_returns_nested_list_structure(self, full_session_df, band_cols):
        """반환값이 list[list[DataFrame]] 구조임"""
        result = split_stimulus_windows(full_session_df, band_cols)
        assert isinstance(result, list)
        assert isinstance(result[0], list)
        assert isinstance(result[0][0], pd.DataFrame)

    def test_n_stimuli_length(self, full_session_df, band_cols):
        """외부 리스트 길이가 n_stimuli와 일치함"""
        result = split_stimulus_windows(full_session_df, band_cols, n_stimuli=10)
        assert len(result) == 10

    def test_n_windows_per_stimulus(self, full_session_df, band_cols):
        """데이터 충분할 때 각 stimulus의 window 수가 올바름"""
        result = split_stimulus_windows(
            full_session_df, band_cols,
            stimulus_duration_sec=60, window_size_sec=10
        )
        # 첫 번째 stimulus는 데이터 충분 → 6개 window
        assert len(result[0]) == 6

    def test_window_row_count(self, full_session_df, band_cols):
        """각 window DataFrame의 행 수가 window_size_sec과 일치함"""
        result = split_stimulus_windows(full_session_df, band_cols, window_size_sec=10)
        assert len(result[0][0]) == 10

    def test_baseline_rows_excluded(self, full_session_df, band_cols):
        """baseline 이전 행이 window에 포함되지 않음"""
        result = split_stimulus_windows(
            full_session_df, band_cols, baseline_duration_sec=30
        )
        # 첫 window의 첫 행은 df.iloc[30]과 동일해야 함
        first_win = result[0][0]
        pd.testing.assert_frame_equal(
            first_win,
            full_session_df[band_cols].iloc[30:40].reset_index(drop=True),
        )

    def test_short_data_partial_windows(self, band_cols):
        """데이터가 짧아 일부 stimulus가 비어있을 때 오류 미발생함"""
        # baseline(30) + 1 stimulus(60) = 90행만 제공, n_stimuli=3 요청
        short_df = pd.DataFrame({
            col: np.random.uniform(0.1, 1.0, 90) for col in band_cols
        })
        result = split_stimulus_windows(
            short_df, band_cols,
            stimulus_duration_sec=60, window_size_sec=10,
            n_stimuli=3, baseline_duration_sec=30
        )
        assert len(result) == 3
        assert len(result[0]) == 6  # 첫 stimulus는 완전함
        # 두 번째, 세 번째 stimulus는 빈 리스트이거나 window 수 부족
        assert len(result[2]) == 0  # 데이터 부족

    def test_window_cols_match_band_cols(self, full_session_df, band_cols):
        """각 window DataFrame의 컬럼이 band_cols와 일치함"""
        result = split_stimulus_windows(full_session_df, band_cols)
        assert list(result[0][0].columns) == band_cols

    def test_index_reset_in_each_window(self, full_session_df, band_cols):
        """각 window DataFrame의 index가 0부터 시작함"""
        result = split_stimulus_windows(full_session_df, band_cols)
        for stim_windows in result:
            for win_df in stim_windows:
                assert win_df.index[0] == 0


# ──────────────────────────────────────────────
# TestExtractFeatures
# ──────────────────────────────────────────────


class TestExtractFeatures:
    def _make_windows(self, n_stim=2, n_win=2, band_cols=None):
        """테스트용 windows 구조 생성함"""
        if band_cols is None:
            band_cols = DEFAULT_BAND_COLS
        windows = []
        for s in range(n_stim):
            stim_wins = []
            for w in range(n_win):
                data = {band: [float(s + w + i) * 0.1 for i in range(10)] for band in band_cols}
                stim_wins.append(pd.DataFrame(data))
            windows.append(stim_wins)
        return windows

    def test_key_naming_convention(self, band_cols):
        """키 형식이 s{N}_w{N}_{band} 패턴임"""
        windows = self._make_windows(1, 1, band_cols)
        result = extract_features(windows, band_cols)
        for key in result.keys():
            parts = key.split("_")
            assert parts[0].startswith("s")
            assert parts[1].startswith("w")
            assert "_".join(parts[2:]) in band_cols

    def test_feature_count_small(self, band_cols):
        """1 stimulus × 1 window × 4 bands → feature 수 = 4"""
        windows = self._make_windows(1, 1, band_cols)
        result = extract_features(windows, band_cols)
        assert len(result) == 4

    def test_full_feature_count(self, band_cols):
        """2 stimulus × 2 windows × 4 bands → feature 수 = 16"""
        windows = self._make_windows(2, 2, band_cols)
        result = extract_features(windows, band_cols)
        assert len(result) == 16

    def test_no_baseline_uses_mean(self, band_cols):
        """baseline=None 시 feature값이 window 평균과 동일함"""
        windows = self._make_windows(1, 1, band_cols)
        result = extract_features(windows, band_cols, baseline=None)
        expected = float(windows[0][0]["alpha"].mean())
        assert abs(result["s1_w1_alpha"] - expected) < 1e-10

    def test_baseline_subtraction(self, band_cols):
        """baseline 제공 시 feature = window_mean - baseline[band]"""
        windows = self._make_windows(1, 1, band_cols)
        baseline = {"alpha": 0.5, "beta": 0.5, "theta": 0.5, "gamma": 0.5}
        result = extract_features(windows, band_cols, baseline=baseline)
        expected = float(windows[0][0]["alpha"].mean()) - 0.5
        assert abs(result["s1_w1_alpha"] - expected) < 1e-10

    def test_returns_ordered_dict(self, band_cols):
        """반환 타입이 OrderedDict임"""
        windows = self._make_windows(1, 1, band_cols)
        result = extract_features(windows, band_cols)
        assert isinstance(result, OrderedDict)

    def test_missing_band_in_window_skipped(self):
        """window DataFrame에 없는 band는 feature에서 건너뜀"""
        windows = [[pd.DataFrame({"alpha": [1.0, 2.0]})]]
        result = extract_features(windows, ["alpha", "nonexistent"])
        assert "s1_w1_alpha" in result
        assert "s1_w1_nonexistent" not in result


# ──────────────────────────────────────────────
# TestBuildPairFeatures
# ──────────────────────────────────────────────


class TestBuildPairFeatures:
    def test_a_prefix_applied(self, sample_features):
        """features_a의 키에 'a_' 접두사가 붙음"""
        result = build_pair_features(sample_features, {})
        for key in sample_features:
            assert f"a_{key}" in result

    def test_b_prefix_applied(self, sample_features):
        """features_b의 키에 'b_' 접두사가 붙음"""
        result = build_pair_features({}, sample_features)
        for key in sample_features:
            assert f"b_{key}" in result

    def test_total_key_count(self, sample_features):
        """결과 dict 키 수 = len(features_a) + len(features_b)"""
        result = build_pair_features(sample_features, sample_features)
        assert len(result) == len(sample_features) * 2

    def test_values_preserved(self):
        """접두사 추가 후에도 원래 float 값과 동일함"""
        fa = {"s1_w1_alpha": 0.123}
        fb = {"s1_w1_alpha": 0.456}
        result = build_pair_features(fa, fb)
        assert result["a_s1_w1_alpha"] == 0.123
        assert result["b_s1_w1_alpha"] == 0.456

    def test_empty_features_allowed(self):
        """빈 dict 입력 시 빈 dict 반환 (오류 없음)"""
        result = build_pair_features({}, {})
        assert result == {}

    def test_a_keys_before_b_keys(self, sample_features):
        """OrderedDict에서 a_ 키가 b_ 키보다 먼저 나옴"""
        result = build_pair_features(sample_features, sample_features)
        keys = list(result.keys())
        a_end = max(i for i, k in enumerate(keys) if k.startswith("a_"))
        b_start = min(i for i, k in enumerate(keys) if k.startswith("b_"))
        assert a_end < b_start


# ──────────────────────────────────────────────
# TestComputeY
# ──────────────────────────────────────────────


class TestComputeY:
    def test_positive_difference(self):
        """abs(7.5 - 6.0) = 1.5"""
        assert compute_y(7.5, 6.0) == 1.5

    def test_reversed_order_same_result(self):
        """abs(6.0 - 7.5) = 1.5 (순서 무관)"""
        assert compute_y(6.0, 7.5) == 1.5

    def test_same_score_returns_zero(self):
        """abs(5.0 - 5.0) = 0.0"""
        assert compute_y(5.0, 5.0) == 0.0

    def test_returns_float(self):
        """반환 타입이 float임"""
        result = compute_y(3.0, 1.0)
        assert isinstance(result, float)


# ──────────────────────────────────────────────
# TestRunFullPipeline
# ──────────────────────────────────────────────


class TestRunFullPipeline:
    @pytest.fixture(autouse=True)
    def _mock_io(self, monkeypatch, full_session_df):
        """CSV I/O와 MindSignalAnalyzer를 mock함"""
        monkeypatch.setattr(
            "server.services.analysis.find_csv_files",
            lambda group_id, idx: [Path(f"/fake/subject_{idx}_{group_id}.csv")],
        )
        monkeypatch.setattr(
            "server.services.analysis.load_session_data",
            lambda path: full_session_df.copy(),
        )
        mock_analyzer = MagicMock()
        mock_analyzer.calculate_synchrony.return_value = 0.75
        monkeypatch.setattr(
            "server.services.analysis.MindSignalAnalyzer",
            lambda: mock_analyzer,
        )

    def test_returns_expected_keys(self):
        """반환 dict에 필수 키 존재함"""
        result = run_full_pipeline(TEST_GROUP_ID, [1, 2])
        expected_keys = {
            "group_id",
            "subjects",
            "pair_features",
            "y_score",
            "synchrony_score",
            "pipeline_params",
            "dataframes",
        }
        assert expected_keys == set(result.keys())

    def test_feature_count_matches_params(self):
        """subjects[i]['n_features'] == n_stimuli * n_windows * len(band_cols)"""
        result = run_full_pipeline(
            TEST_GROUP_ID, [1, 2],
            n_stimuli=10, window_size_sec=10, stimulus_duration_sec=60
        )
        expected_count = 10 * 6 * 4  # n_stimuli × n_windows × n_bands
        assert result["subjects"][0]["n_features"] == expected_count

    def test_with_satisfaction_scores(self):
        """satisfaction_scores 제공 시 y_score가 float임"""
        result = run_full_pipeline(
            TEST_GROUP_ID, [1, 2],
            satisfaction_scores={1: 7.5, 2: 6.0},
        )
        assert isinstance(result["y_score"], float)
        assert result["y_score"] == 1.5

    def test_without_satisfaction_scores(self):
        """satisfaction_scores=None 시 y_score도 None임"""
        result = run_full_pipeline(TEST_GROUP_ID, [1, 2])
        assert result["y_score"] is None

    def test_pair_features_with_two_subjects(self):
        """subject 2명일 때 pair_features 존재함"""
        result = run_full_pipeline(TEST_GROUP_ID, [1, 2])
        assert result["pair_features"] is not None
        # a_ 키와 b_ 키 모두 존재해야 함
        keys = list(result["pair_features"].keys())
        assert any(k.startswith("a_") for k in keys)
        assert any(k.startswith("b_") for k in keys)

    def test_csv_not_found(self, monkeypatch):
        """CSV 미존재 subject는 error 키 포함함"""
        monkeypatch.setattr(
            "server.services.analysis.find_csv_files",
            lambda group_id, idx: [],  # 빈 리스트 반환
        )
        result = run_full_pipeline(TEST_GROUP_ID, [1])
        assert "error" in result["subjects"][0]

    def test_band_cols_default(self):
        """band_cols=None 시 기본값 사용됨"""
        result = run_full_pipeline(TEST_GROUP_ID, [1, 2])
        assert result["pipeline_params"]["band_cols"] == ["alpha", "beta", "theta", "gamma"]

    def test_synchrony_score_mocked(self):
        """MindSignalAnalyzer.calculate_synchrony Mock → 0.75 반환함"""
        result = run_full_pipeline(TEST_GROUP_ID, [1, 2])
        assert result["synchrony_score"] == 0.75
