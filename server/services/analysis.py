from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd

from core.analyzer import MindSignalAnalyzer
from server.config import settings

# CSV 저장 기본 경로 (streamer.py와 동일한 위치)
CSV_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "csv"


def find_csv_files(group_id: str, subject_index: int) -> list[Path]:
    """특정 그룹/피실험자의 CSV 파일을 검색함"""
    pattern = f"subject_{subject_index}_{group_id}_*.csv"
    return sorted(
        CSV_BASE_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True
    )


def load_session_data(csv_path: Path) -> pd.DataFrame:
    """CSV 파일을 DataFrame으로 로드함"""
    return pd.read_csv(csv_path)


def compute_subject_summary(df: pd.DataFrame) -> dict:
    """단일 피실험자의 세션 요약 통계를 계산함"""
    metric_cols = [
        "focus",
        "engagement",
        "interest",
        "excitement",
        "stress",
        "relaxation",
    ]
    wave_cols = ["delta", "theta", "alpha", "beta", "gamma"]

    summary = {
        "metrics_mean": {
            col: float(df[col].mean()) for col in metric_cols if col in df.columns
        },
        "metrics_std": {
            col: float(df[col].std()) for col in metric_cols if col in df.columns
        },
        "waves_mean": {
            col: float(df[col].mean()) for col in wave_cols if col in df.columns
        },
        "total_samples": len(df),
        "duration_seconds": len(df),  # 1초당 1샘플
    }
    return summary


def compute_synchrony(df1: pd.DataFrame, df2: pd.DataFrame) -> float | None:
    """두 피실험자 간 뇌파 동기화 점수를 계산함"""
    analyzer = MindSignalAnalyzer()

    # 공통 길이로 맞춤
    min_len = min(len(df1), len(df2))
    if min_len < 10:
        return None

    # alpha 대역 기준 동기화 계산 수행함
    alpha1 = df1["alpha"].values[:min_len]
    alpha2 = df2["alpha"].values[:min_len]

    return float(analyzer.calculate_synchrony(alpha1, alpha2))


def compute_session_analysis(group_id: str, subject_indices: list[int]) -> dict:
    """그룹 세션의 전체 분석을 수행함"""
    subjects = []
    dataframes = {}

    for idx in subject_indices:
        csv_files = find_csv_files(group_id, idx)
        if not csv_files:
            subjects.append({"subject_index": idx, "error": "CSV 파일 미발견"})
            continue

        df = load_session_data(csv_files[0])  # 가장 최신 파일 사용
        dataframes[idx] = df
        summary = compute_subject_summary(df)
        subjects.append({"subject_index": idx, **summary})

    # 두 명의 피실험자가 있을 때 동기화 점수 계산 수행함
    synchrony_score = None
    if len(dataframes) == 2:
        keys = list(dataframes.keys())
        synchrony_score = compute_synchrony(dataframes[keys[0]], dataframes[keys[1]])

    return {
        "group_id": group_id,
        "subjects": subjects,
        "synchrony_score": synchrony_score,
        "dataframes": dataframes,  # Markdown 변환용 (응답에서는 제외됨)
    }


# ──────────────────────────────────────────────
# 파이프라인 단계별 함수 (알고리즘 명세 기반)
# ──────────────────────────────────────────────


def average_by_timestamp(df: pd.DataFrame, band_cols: list[str]) -> pd.DataFrame:
    """타임스탬프별 뇌파 신호를 평균화하여 노이즈를 감소시킴

    각 timestamp에서 측정된 원시 뇌파 신호가 여러 샘플인 경우,
    평균값으로 변환하여 대표값을 설정함.
    CSV가 이미 1초 1행이면 그대로 반환함.
    """
    # 'time' 또는 'timestamp' 컬럼 유무 확인
    time_col = None
    if "time" in df.columns:
        time_col = "time"
    elif "timestamp" in df.columns:
        time_col = "timestamp"

    if time_col is None:
        # 이미 1초 1행 구조로 가정하여 band_cols만 추출하여 반환함
        available = [c for c in band_cols if c in df.columns]
        return df[available].reset_index(drop=True)

    # 타임스탬프 기준 groupby 후 band_cols의 mean 계산 수행함
    available = [c for c in band_cols if c in df.columns]
    grouped = df.groupby(time_col)[available].mean().reset_index(drop=True)
    return grouped


def compute_baseline(
    df: pd.DataFrame,
    band_cols: list[str],
    baseline_duration_sec: int = 30,
) -> dict[str, float]:
    """Baseline 구간(처음 N초)의 대역별 평균값을 산출함"""
    # 처음 baseline_duration_sec 행을 baseline 구간으로 사용함 (1행 = 1초 가정)
    baseline_df = df.iloc[:baseline_duration_sec]
    result = {}
    for band in band_cols:
        if band in baseline_df.columns:
            result[band] = float(baseline_df[band].mean())
    return result


def split_stimulus_windows(
    df: pd.DataFrame,
    band_cols: list[str],
    stimulus_duration_sec: int = 60,
    window_size_sec: int = 10,
    n_stimuli: int = 10,
    baseline_duration_sec: int = 30,
) -> list[list[pd.DataFrame]]:
    """Stimulus 구간을 윈도우 단위로 분할함

    baseline 구간 이후의 데이터를 stimulus별 → window별로 분할함.
    반환: windows[stimulus_idx][window_idx] = DataFrame (band_cols만 포함)
    """
    n_windows = stimulus_duration_sec // window_size_sec
    available = [c for c in band_cols if c in df.columns]
    windows: list[list[pd.DataFrame]] = []

    for stim_idx in range(n_stimuli):
        # 각 stimulus의 시작 행 인덱스 계산함
        stimulus_start = baseline_duration_sec + (stim_idx * stimulus_duration_sec)
        stim_windows: list[pd.DataFrame] = []

        for win_idx in range(n_windows):
            win_start = stimulus_start + (win_idx * window_size_sec)
            win_end = win_start + window_size_sec

            # 데이터가 부족한 경우 해당 window 건너뜀
            if win_start >= len(df):
                break

            window_df = df[available].iloc[win_start:win_end].reset_index(drop=True)

            # 실제 데이터가 존재하는 경우만 추가함
            if len(window_df) > 0:
                stim_windows.append(window_df)

        windows.append(stim_windows)

    return windows


def extract_features(
    windows: list[list[pd.DataFrame]],
    band_cols: list[str],
    baseline: dict[str, float] | None = None,
) -> dict[str, float]:
    """윈도우별 × 대역별 feature를 추출함

    네이밍 컨벤션: s{stimulus_idx}_w{window_idx}_{band}
    baseline이 주어지면 baseline 대비 변화량으로 feature 계산함.
    """
    features: dict[str, float] = OrderedDict()

    for stim_idx, stim_windows in enumerate(windows):
        for win_idx, window_df in enumerate(stim_windows):
            for band in band_cols:
                if band not in window_df.columns:
                    continue
                window_mean = float(window_df[band].mean())

                # baseline이 있으면 baseline 대비 변화량으로 계산함
                if baseline is not None and band in baseline:
                    feature_val = window_mean - baseline[band]
                else:
                    feature_val = window_mean

                # 1-indexed 키 네이밍 적용함
                key = f"s{stim_idx + 1}_w{win_idx + 1}_{band}"
                features[key] = feature_val

    return features


def build_pair_features(
    features_a: dict[str, float],
    features_b: dict[str, float],
) -> dict[str, float]:
    """두 피실험자의 feature를 결합하여 pair feature를 구성함"""
    pair: dict[str, float] = OrderedDict()

    # Subject A feature에 "a_" 접두사 추가함
    for key, val in features_a.items():
        pair[f"a_{key}"] = val

    # Subject B feature에 "b_" 접두사 추가함
    for key, val in features_b.items():
        pair[f"b_{key}"] = val

    return pair


def compute_y(satisfaction_a: float, satisfaction_b: float) -> float:
    """두 참가자의 관계 만족도 차이를 계산함 (타겟 변수)"""
    return abs(satisfaction_a - satisfaction_b)


def run_full_pipeline(
    group_id: str,
    subject_indices: list[int],
    stimulus_duration_sec: int = 60,
    window_size_sec: int = 10,
    n_stimuli: int = 10,
    baseline_duration_sec: int = 30,
    band_cols: list[str] | None = None,
    satisfaction_scores: dict[int, float] | None = None,
) -> dict:
    """알고리즘 명세의 전체 파이프라인을 실행함

    [1] CSV 로드 → [2] 타임스탬프별 평균화 → [3] Baseline 산출
    → [4] Stimulus 윈도우 분할 → [5] Feature 추출
    → [7] Pair Feature 구성 → [8] Y 계산
    """
    # band_cols 기본값 설정함
    if band_cols is None:
        band_cols = ["alpha", "beta", "theta", "gamma"]

    n_windows_per_stimulus = stimulus_duration_sec // window_size_sec
    total_features_per_subject = n_stimuli * n_windows_per_stimulus * len(band_cols)

    subjects_result = []
    subject_features: dict[int, dict[str, float]] = {}
    dataframes: dict[int, pd.DataFrame] = {}

    for idx in subject_indices:
        # [1] CSV 로드 수행함
        csv_files = find_csv_files(group_id, idx)
        if not csv_files:
            subjects_result.append({"subject_index": idx, "error": "CSV 파일 미발견"})
            continue

        raw_df = load_session_data(csv_files[0])
        dataframes[idx] = raw_df

        # [2] 타임스탬프별 평균화 수행함
        averaged_df = average_by_timestamp(raw_df, band_cols)

        # [3] Baseline 산출 수행함
        baseline = compute_baseline(averaged_df, band_cols, baseline_duration_sec)

        # [4] Stimulus 윈도우 분할 수행함
        windows = split_stimulus_windows(
            averaged_df,
            band_cols,
            stimulus_duration_sec=stimulus_duration_sec,
            window_size_sec=window_size_sec,
            n_stimuli=n_stimuli,
            baseline_duration_sec=baseline_duration_sec,
        )

        # [5] Feature 추출 수행함
        features = extract_features(windows, band_cols, baseline=baseline)

        subject_features[idx] = features
        subjects_result.append(
            {
                "subject_index": idx,
                "baseline": baseline,
                "features": features,
                "n_features": len(features),
            }
        )

    # [7] Pair Feature 구성 (subject 2명일 때만 수행함)
    pair_features = None
    if len(subject_indices) == 2:
        idx_a, idx_b = subject_indices[0], subject_indices[1]
        if idx_a in subject_features and idx_b in subject_features:
            pair_features = build_pair_features(
                subject_features[idx_a], subject_features[idx_b]
            )

    # [8] Y 계산 (satisfaction_scores가 있을 때만 수행함)
    y_score = None
    if satisfaction_scores is not None and len(subject_indices) == 2:
        idx_a, idx_b = subject_indices[0], subject_indices[1]
        if idx_a in satisfaction_scores and idx_b in satisfaction_scores:
            y_score = compute_y(satisfaction_scores[idx_a], satisfaction_scores[idx_b])

    # 기존 compute_synchrony를 활용한 synchrony_score 계산 수행함
    synchrony_score = None
    if len(dataframes) == 2:
        keys = list(dataframes.keys())
        synchrony_score = compute_synchrony(dataframes[keys[0]], dataframes[keys[1]])

    return {
        "group_id": group_id,
        "subjects": subjects_result,
        "pair_features": pair_features,
        "y_score": y_score,
        "synchrony_score": synchrony_score,
        "pipeline_params": {
            "stimulus_duration_sec": stimulus_duration_sec,
            "window_size_sec": window_size_sec,
            "n_stimuli": n_stimuli,
            "baseline_duration_sec": baseline_duration_sec,
            "band_cols": band_cols,
            "n_windows_per_stimulus": n_windows_per_stimulus,
            "total_features_per_subject": total_features_per_subject,
        },
        "dataframes": dataframes,  # Markdown 변환용
    }
