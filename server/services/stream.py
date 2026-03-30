"""EEG 스트리밍 프로세스 관리 서비스임"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# 엔진 루트 디렉토리 (stream.py → server/services/ → server/ → engine root)
_ENGINE_ROOT = str(Path(__file__).resolve().parent.parent.parent)

# 실행 중인 스트리밍 프로세스 추적 dict — key: "{group_id}:{subject_index}"
_processes: dict[str, subprocess.Popen] = {}


def _make_key(group_id: str, subject_index: int) -> str:
    """프로세스 식별 키 생성함"""
    return f"{group_id}:{subject_index}"


def start_stream(group_id: str, subject_index: int) -> dict[str, Any]:
    """core.main을 자식 프로세스로 spawn하여 EEG 스트리밍 시작함"""
    key = _make_key(group_id, subject_index)

    # 이미 실행 중인 프로세스 확인함
    if key in _processes:
        proc = _processes[key]
        if proc.poll() is None:
            raise RuntimeError(f"스트림이 이미 실행 중임: {key} (PID {proc.pid})")
        # 이미 종료된 프로세스는 정리함
        del _processes[key]

    proc = subprocess.Popen(
        [sys.executable, "-m", "core.main", group_id, str(subject_index)],
        env=os.environ.copy(),
        cwd=_ENGINE_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    _processes[key] = proc
    return {"status": "started", "pid": proc.pid, "key": key}


def stop_stream(group_id: str, subject_index: int) -> dict[str, Any]:
    """실행 중인 EEG 스트리밍 프로세스 종료함"""
    key = _make_key(group_id, subject_index)

    if key not in _processes:
        raise KeyError(f"실행 중인 스트림을 찾을 수 없음: {key}")

    proc = _processes[key]

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    del _processes[key]
    return {"status": "stopped", "key": key}


def get_all_status() -> list[dict[str, Any]]:
    """모든 스트리밍 프로세스 상태 조회 및 종료된 프로세스 자동 정리함"""
    result = []
    finished_keys = []

    for key, proc in _processes.items():
        running = proc.poll() is None
        entry = {"key": key, "pid": proc.pid, "running": running}

        if not running:
            entry["returncode"] = proc.returncode
            finished_keys.append(key)

        result.append(entry)

    # 종료된 프로세스 자동 정리함
    for key in finished_keys:
        del _processes[key]

    return result
