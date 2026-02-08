"""Tests for ox.cli — Typer-based CLI commands."""

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ox.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestRootCommand:
    def test_outside_project(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Not inside an ox project" in result.output

    def test_inside_project_no_experiments(
        self, runner: CliRunner, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "test-project" in result.output
        assert "studies: 0" in result.output
        assert "experiments: 0" in result.output
        assert "No experiments yet" in result.output

    def test_inside_project_with_experiments(
        self,
        runner: CliRunner,
        tmp_project: Path,
        sample_experiment: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "test-project" in result.output
        assert "studies: 1" in result.output
        assert "experiments: 1" in result.output
        assert "1 completed" in result.output


class TestInit:
    def test_creates_project_structure(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["init", "my-research"])
        assert result.exit_code == 0, result.output

        project = tmp_path / "my-research"
        assert project.exists()
        assert (project / "ox.yaml").exists()
        assert (project / "CLAUDE.md").exists()
        assert (project / "pyproject.toml").exists()
        assert (project / ".gitignore").exists()
        assert (project / "studies").exists()
        assert (project / "src" / "my_research" / "__init__.py").exists()
        assert (project / "src" / "my_research" / "scripts" / "train.py").exists()
        assert (project / ".claude" / "skills").exists()

    def test_ox_yaml_content(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "test-proj"])
        content = yaml.safe_load((tmp_path / "test-proj" / "ox.yaml").read_text())
        assert content["project"]["name"] == "test-proj"

    def test_initializes_git(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(cli, ["init", "git-test"])
        assert (tmp_path / "git-test" / ".git").exists()

    def test_fails_if_exists(
        self, runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "existing").mkdir()
        result = runner.invoke(cli, ["init", "existing"])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestNewStudy:
    def test_creates_study(
        self, runner: CliRunner, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["new", "study", "sparse attention"])
        assert result.exit_code == 0, result.output

        study_dir = tmp_project / "studies" / "sparse-attention"
        assert study_dir.exists()
        assert (study_dir / "README.md").exists()
        assert (study_dir / "experiments").exists()

    def test_fails_if_exists(
        self, runner: CliRunner, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_project)
        runner.invoke(cli, ["new", "study", "test"])
        result = runner.invoke(cli, ["new", "study", "test"])
        assert result.exit_code != 0
        assert "already exists" in result.output


class TestNewExperiment:
    def test_creates_experiment(
        self, runner: CliRunner, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_project)
        runner.invoke(cli, ["new", "study", "my-study"])
        result = runner.invoke(cli, ["new", "experiment", "my-study", "baseline", "-t", "test"])
        assert result.exit_code == 0, result.output

        exp_dir = tmp_project / "studies" / "my-study" / "experiments" / "baseline"
        assert (exp_dir / "experiment.json").exists()
        assert (exp_dir / "config.yaml").exists()
        assert (exp_dir / "NOTES.md").exists()

        data = json.loads((exp_dir / "experiment.json").read_text())
        assert data["id"] == "baseline"
        assert data["study"] == "my-study"
        assert data["status"] == "created"
        assert "test" in data["tags"]

    def test_fails_without_study(
        self, runner: CliRunner, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["new", "experiment", "nonexistent", "exp1"])
        assert result.exit_code != 0
        assert "Study not found" in result.output


class TestRun:
    def test_warns_outside_project(
        self,
        runner: CliRunner,
        tmp_path: Path,
        tmp_script: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["run", str(tmp_script)])
        assert result.exit_code == 0, result.output
        assert "Warning: not inside an ox project" in result.output
        assert "Run completed" in result.output

    def test_experiment_fails_outside_project(
        self,
        runner: CliRunner,
        tmp_path: Path,
        tmp_script: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["run", str(tmp_script), "--experiment", "foo"])
        assert result.exit_code != 0
        assert "Cannot use --experiment outside an ox project" in result.output

    def test_runs_script(
        self,
        runner: CliRunner,
        tmp_project: Path,
        tmp_script: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["run", str(tmp_script)])
        assert result.exit_code == 0, result.output
        assert "Run completed" in result.output

    def test_runs_with_overrides(
        self,
        runner: CliRunner,
        tmp_project: Path,
        tmp_script: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["run", str(tmp_script), "--", "--epochs", "2"])
        assert result.exit_code == 0, result.output

    def test_runs_with_config_file(
        self,
        runner: CliRunner,
        tmp_project: Path,
        tmp_script: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        config = tmp_project / "run_config.yaml"
        config.write_text(yaml.dump({"epochs": 2, "lr": 0.1}))
        result = runner.invoke(cli, ["run", str(tmp_script), "--config", str(config)])
        assert result.exit_code == 0, result.output

    def test_runs_with_experiment(
        self,
        runner: CliRunner,
        tmp_project: Path,
        tmp_script: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        runner.invoke(cli, ["new", "study", "s"])
        runner.invoke(cli, ["new", "experiment", "s", "e"])

        config = tmp_project / "studies" / "s" / "experiments" / "e" / "config.yaml"
        config.write_text(yaml.dump({"epochs": 1}))

        result = runner.invoke(
            cli, ["run", str(tmp_script), "--config", str(config), "--experiment", "e"]
        )
        assert result.exit_code == 0, result.output

        data = json.loads(
            (tmp_project / "studies" / "s" / "experiments" / "e" / "experiment.json").read_text()
        )
        assert data["status"] == "completed"


class TestLs:
    def test_lists_experiments(
        self,
        runner: CliRunner,
        tmp_project: Path,
        sample_experiment: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["ls"])
        assert result.exit_code == 0
        assert "test-exp" in result.output

    def test_filter_by_study(
        self,
        runner: CliRunner,
        tmp_project: Path,
        sample_experiment: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["ls", "--study", "test-study"])
        assert "test-exp" in result.output

    def test_filter_by_status(
        self,
        runner: CliRunner,
        tmp_project: Path,
        sample_experiment: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["ls", "--status", "completed"])
        assert "test-exp" in result.output

        result = runner.invoke(cli, ["ls", "--status", "running"])
        assert "No experiments" in result.output

    def test_filter_by_tag(
        self,
        runner: CliRunner,
        tmp_project: Path,
        sample_experiment: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["ls", "--tag", "baseline"])
        assert "test-exp" in result.output

    def test_empty(
        self, runner: CliRunner, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["ls"])
        assert "No experiments" in result.output


class TestQuery:
    def test_basic_query(
        self,
        runner: CliRunner,
        tmp_project: Path,
        sample_experiment: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["query", "status = 'completed'"])
        assert result.exit_code == 0
        assert "test-exp" in result.output

    def test_no_results(
        self,
        runner: CliRunner,
        tmp_project: Path,
        sample_experiment: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["query", "status = 'running'"])
        assert "No matching" in result.output


class TestShow:
    def test_shows_experiment(
        self,
        runner: CliRunner,
        tmp_project: Path,
        sample_experiment: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["show", "test-exp"])
        assert result.exit_code == 0
        assert "test-exp" in result.output
        assert "completed" in result.output
        assert "abc123" in result.output

    def test_shows_config(
        self,
        runner: CliRunner,
        tmp_project: Path,
        sample_experiment: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["show", "test-exp"])
        assert "lr: 0.001" in result.output

    def test_shows_notes(
        self,
        runner: CliRunner,
        tmp_project: Path,
        sample_experiment: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["show", "test-exp"])
        assert "Some notes" in result.output

    def test_not_found(
        self, runner: CliRunner, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["show", "nope"])
        assert result.exit_code != 0


class TestStatus:
    def test_no_running(
        self, runner: CliRunner, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_project)
        result = runner.invoke(cli, ["status"])
        assert "No experiments currently running" in result.output


class TestConfigSchema:
    def test_prints_schema(self, runner: CliRunner, tmp_script: Path) -> None:
        result = runner.invoke(cli, ["config-schema", str(tmp_script)])
        assert result.exit_code == 0
        schema = json.loads(result.output)
        assert "properties" in schema
        assert "lr" in schema["properties"]

    def test_not_found(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(cli, ["config-schema", str(tmp_path / "nope.py")])
        assert result.exit_code != 0
