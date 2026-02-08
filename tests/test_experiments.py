"""Tests for ox.experiments — metadata read/write/query."""

from __future__ import annotations

from pathlib import Path

import pytest

from ox.experiments import (
    Experiment,
    Status,
    find_all_experiments,
    find_experiment,
    find_project_root,
    load_all_experiments,
    load_experiment,
    now_iso,
    query_experiments,
    save_experiment,
)


class TestStatus:
    def test_string_serialization(self) -> None:
        assert Status.COMPLETED.value == "completed"
        assert Status("running") == Status.RUNNING

    def test_all_values(self) -> None:
        expected = {"created", "running", "completed", "failed", "cancelled"}
        assert {s.value for s in Status} == expected


class TestExperiment:
    def test_to_dict(self) -> None:
        exp = Experiment(
            id="test",
            study="study",
            status=Status.CREATED,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            tags=["a", "b"],
        )
        d = exp.to_dict()
        assert d["id"] == "test"
        assert d["status"] == "created"
        assert d["tags"] == ["a", "b"]
        assert "config" not in d  # config excluded from JSON

    def test_from_dict(self) -> None:
        data = {
            "id": "test",
            "study": "study",
            "status": "completed",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T01:00:00",
            "git_sha": "abc123",
            "tags": ["x"],
        }
        exp = Experiment.from_dict(data)
        assert exp.id == "test"
        assert exp.status == Status.COMPLETED
        assert exp.git_sha == "abc123"

    def test_roundtrip(self) -> None:
        exp = Experiment(
            id="rt",
            study="s",
            status=Status.RUNNING,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            git_sha="def456",
            command="ox run train.py",
            tags=["test"],
            tracker_run_id="run-1",
        )
        restored = Experiment.from_dict(exp.to_dict())
        assert restored.id == exp.id
        assert restored.status == exp.status
        assert restored.git_sha == exp.git_sha
        assert restored.tags == exp.tags


class TestFindProjectRoot:
    def test_finds_root(self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_project)
        assert find_project_root() == tmp_project

    def test_finds_root_from_subdirectory(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        subdir = tmp_project / "studies" / "deep"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)
        assert find_project_root() == tmp_project

    def test_raises_when_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError, match=r"Could not find ox\.yaml"):
            find_project_root()


class TestFindAllExperiments:
    def test_finds_experiments(self, sample_experiment: Path, tmp_project: Path) -> None:
        paths = find_all_experiments(tmp_project)
        assert len(paths) == 1
        assert paths[0].name == "experiment.json"

    def test_empty_project(self, tmp_project: Path) -> None:
        assert find_all_experiments(tmp_project) == []


class TestLoadAndSaveExperiment:
    def test_load_experiment(self, sample_experiment: Path) -> None:
        exp = load_experiment(sample_experiment / "experiment.json")
        assert exp.id == "test-exp"
        assert exp.study == "test-study"
        assert exp.status == Status.COMPLETED
        assert exp.config["lr"] == 0.001

    def test_save_and_load(self, tmp_path: Path) -> None:
        exp = Experiment(
            id="save-test",
            study="s",
            status=Status.CREATED,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        path = tmp_path / "experiment.json"
        save_experiment(exp, path)
        assert path.exists()

        loaded = load_experiment(path)
        assert loaded.id == "save-test"
        assert loaded.status == Status.CREATED

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        exp = Experiment(
            id="deep",
            study="s",
            status=Status.CREATED,
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        path = tmp_path / "a" / "b" / "experiment.json"
        save_experiment(exp, path)
        assert path.exists()


class TestLoadAllExperiments:
    def test_loads_all(self, sample_experiment: Path, tmp_project: Path) -> None:
        experiments = load_all_experiments(tmp_project)
        assert len(experiments) == 1
        assert experiments[0].id == "test-exp"

    def test_skips_malformed(self, tmp_project: Path) -> None:
        exp_dir = tmp_project / "studies" / "bad" / "experiments" / "broken"
        exp_dir.mkdir(parents=True)
        (exp_dir / "experiment.json").write_text("not json")
        experiments = load_all_experiments(tmp_project)
        assert len(experiments) == 0


class TestFindExperiment:
    def test_finds_by_id(self, sample_experiment: Path, tmp_project: Path) -> None:
        exp, path = find_experiment("test-exp", tmp_project)
        assert exp.id == "test-exp"
        assert path.name == "experiment.json"

    def test_raises_on_not_found(self, tmp_project: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Experiment not found"):
            find_experiment("nonexistent", tmp_project)


class TestQueryExperiments:
    def test_query_by_status(self, sample_experiment: Path, tmp_project: Path) -> None:
        results = query_experiments("status = 'completed'", tmp_project)
        assert len(results) == 1
        assert results[0]["id"] == "test-exp"

    def test_query_config_fields(self, sample_experiment: Path, tmp_project: Path) -> None:
        results = query_experiments("lr < 0.01", tmp_project)
        assert len(results) == 1

    def test_query_no_results(self, sample_experiment: Path, tmp_project: Path) -> None:
        results = query_experiments("status = 'running'", tmp_project)
        assert len(results) == 0

    def test_query_empty_project(self, tmp_project: Path) -> None:
        results = query_experiments("status = 'completed'", tmp_project)
        assert len(results) == 0

    def test_invalid_query(self, sample_experiment: Path, tmp_project: Path) -> None:
        with pytest.raises(ValueError, match="Query error"):
            query_experiments("INVALID SQL GARBAGE !!!", tmp_project)


class TestNowIso:
    def test_returns_string(self) -> None:
        result = now_iso()
        assert isinstance(result, str)
        assert "T" in result
