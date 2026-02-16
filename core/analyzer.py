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

    # --- 5가지 주요 파형 필터 ---
    def filter_delta(self, data): return lfilter(*self._butter_bandpass(0.5, 4), data)
    def filter_theta(self, data): return lfilter(*self._butter_bandpass(4, 8), data)
    def filter_alpha(self, data): return lfilter(*self._butter_bandpass(8, 12), data)
    def filter_beta(self, data):  return lfilter(*self._butter_bandpass(13, 30), data)
    def filter_gamma(self, data): return lfilter(*self._butter_bandpass(30, 45), data)

    def get_rms_power(self, filtered_data):
        """필터링된 신호의 강도(RMS) 계산"""
        # 신호의 크기를 수치화하여 '현재 알파파가 얼마나 강한지' 판단할 때 씁니다.
        return np.sqrt(np.mean(np.square(filtered_data)))

    def get_all_powers(self, eeg_values):
        """5개 파형의 강도를 한 번에 계산하여 반환"""
        return {
            "delta": self.get_rms_power(self.filter_delta(eeg_values)),
            "theta": self.get_rms_power(self.filter_theta(eeg_values)),
            "alpha": self.get_rms_power(self.filter_alpha(eeg_values)),
            "beta":  self.get_rms_power(self.filter_beta(eeg_values)),
            "gamma": self.get_rms_power(self.filter_gamma(eeg_values)),
        }    
