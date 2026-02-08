"""Tests for ox.tracker — Tracker protocol and backends."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ox.tracker import LocalTracker, Tracker, get_tracker


class TestTrackerProtocol:
    def test_local_tracker_is_tracker(self) -> None:
        assert isinstance(LocalTracker(), Tracker)


class TestLocalTracker:
    def test_init_run_creates_file(self, tmp_path: Path) -> None:
        tracker = LocalTracker(output_dir=tmp_path)
        tracker.init_run("test-run", {"lr": 0.01})
        tracker.finish()

        path = tmp_path / "test-run_metrics.jsonl"
        assert path.exists()

    def test_writes_config_entry(self, tmp_path: Path) -> None:
        tracker = LocalTracker(output_dir=tmp_path)
        tracker.init_run("test-run", {"lr": 0.01})
        tracker.finish()

        lines = _read_jsonl(tmp_path / "test-run_metrics.jsonl")
        config_entry = lines[0]
        assert config_entry["type"] == "config"
        assert config_entry["run_id"] == "test-run"
        assert config_entry["config"] == {"lr": 0.01}

    def test_log_writes_metrics(self, tmp_path: Path) -> None:
        tracker = LocalTracker(output_dir=tmp_path)
        tracker.init_run("test-run", {})
        tracker.log({"loss": 0.5, "acc": 0.8}, step=1)
        tracker.log({"loss": 0.3, "acc": 0.9}, step=2)
        tracker.finish()

        lines = _read_jsonl(tmp_path / "test-run_metrics.jsonl")
        metrics = [entry for entry in lines if entry["type"] == "metrics"]
        assert len(metrics) == 2
        assert metrics[0]["loss"] == 0.5
        assert metrics[0]["step"] == 1
        assert metrics[1]["loss"] == 0.3

    def test_log_without_step(self, tmp_path: Path) -> None:
        tracker = LocalTracker(output_dir=tmp_path)
        tracker.init_run("test-run", {})
        tracker.log({"final_loss": 0.1})
        tracker.finish()

        lines = _read_jsonl(tmp_path / "test-run_metrics.jsonl")
        metrics = [entry for entry in lines if entry["type"] == "metrics"]
        assert len(metrics) == 1
        assert "step" not in metrics[0]
        assert metrics[0]["final_loss"] == 0.1

    def test_finish_writes_finish_entry(self, tmp_path: Path) -> None:
        tracker = LocalTracker(output_dir=tmp_path)
        tracker.init_run("test-run", {})
        tracker.log({"loss": 0.5}, step=5)
        tracker.finish()

        lines = _read_jsonl(tmp_path / "test-run_metrics.jsonl")
        finish_entry = next(entry for entry in lines if entry["type"] == "finish")
        assert finish_entry["run_id"] == "test-run"
        assert finish_entry["total_steps"] == 5

    def test_finish_is_idempotent(self, tmp_path: Path) -> None:
        tracker = LocalTracker(output_dir=tmp_path)
        tracker.init_run("test-run", {})
        tracker.finish()
        tracker.finish()  # should not raise

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        output = tmp_path / "nested" / "dir"
        tracker = LocalTracker(output_dir=output)
        tracker.init_run("test-run", {})
        tracker.finish()
        assert output.exists()


class TestGetTracker:
    def test_returns_local_tracker_from_config(self, tmp_path: Path) -> None:
        config = {"backend": "local", "output_dir": str(tmp_path)}
        tracker = get_tracker(config)
        assert isinstance(tracker, LocalTracker)

    def test_raises_on_unknown_backend(self) -> None:
        with pytest.raises(ValueError, match="Unknown tracker backend"):
            get_tracker({"backend": "nonsense"})


def _read_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
