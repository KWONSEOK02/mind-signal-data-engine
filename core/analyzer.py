import numpy as np
from scipy.signal import butter, lfilter, welch


class MindSignalAnalyzer:
    @staticmethod
    def calculate_faa(eeg_data, ch_left_idx, ch_right_idx):
        """
        FAA(Frontal Alpha Asymmetry) 계산 로직
        공식: ln(Right Alpha) - ln(Left Alpha)
        """
        # 1. Welch 방법을 이용한 주파수 밀도(PSD) 계산
        fs = 128  # Emotiv Insight 샘플링 레이트
        freqs, psd = welch(eeg_data, fs, nperseg=fs * 2)

        # 2. Alpha 대역(8-13Hz) 추출
        alpha_mask = (freqs >= 8) & (freqs <= 13)
        alpha_power = np.mean(psd[:, alpha_mask], axis=1)

        # 3. 비대칭 지수 계산
        left_alpha = alpha_power[ch_left_idx]
        right_alpha = alpha_power[ch_right_idx]

        faa_score = np.log(right_alpha) - np.log(left_alpha)
        return faa_score

    @staticmethod
    def calculate_synchrony(user1_eeg, user2_eeg):
        """두 사용자 간의 뇌파 동기화(Correlation) 계산"""
        correlation = np.corrcoef(user1_eeg, user2_eeg)[0, 1]
        return correlation

    def __init__(self, sampling_rate=128):
        # Emotiv Insight의 샘플링 레이트는 초당 128Hz입니다.
        self.fs = sampling_rate

    def _butter_bandpass(self, lowcut, highcut, order=5):
        """버터워스 필터 계수 계산"""
        nyq = 0.5 * self.fs
        low = lowcut / nyq
        high = highcut / nyq
        b, a = butter(order, [low, high], btype="band")
        return b, a

    def filter_alpha(self, data):
        """알파파(8-12Hz) 추출: 휴식 및 차분한 상태 분석용"""
        b, a = self._butter_bandpass(8, 12, order=5)
        return lfilter(b, a, data)

    def filter_beta(self, data):
        """베타파(13-30Hz) 추출: 각성 및 집중 상태 분석용"""
        b, a = self._butter_bandpass(13, 30, order=5)
        return lfilter(b, a, data)

    def get_rms_power(self, filtered_data):
        """필터링된 신호의 강도(RMS) 계산"""
        # 신호의 크기를 수치화하여 '현재 알파파가 얼마나 강한지' 판단할 때 씁니다.
        return np.sqrt(np.mean(np.square(filtered_data)))
