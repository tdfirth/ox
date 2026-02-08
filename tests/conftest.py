"""Shared test fixtures for ox tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal ox project structure for testing."""
    (tmp_path / "ox.yaml").write_text(
        yaml.dump(
            {
                "project": {"name": "test-project"},
                "tracker": {"backend": "local", "output_dir": str(tmp_path / ".ox" / "metrics")},
            }
        )
    )
    (tmp_path / "studies").mkdir()
    (tmp_path / ".ox" / "metrics").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def tmp_script(tmp_path: Path) -> Path:
    """Create a valid training script for testing."""
    script = tmp_path / "train.py"
    script.write_text(
        "from pydantic import BaseModel\n"
        "\n"
        "\n"
        "class Config(BaseModel):\n"
        "    lr: float = 1e-3\n"
        "    batch_size: int = 32\n"
        "    epochs: int = 10\n"
        "    name: str = 'default'\n"
        "    debug: bool = False\n"
        "\n"
        "\n"
        "def main(config, tracker):\n"
        "    for i in range(config.epochs):\n"
        "        tracker.log({'loss': 1.0 / (i + 1)}, step=i)\n"
    )
    return script


@pytest.fixture
def sample_experiment(tmp_project: Path) -> Path:
    """Create a sample experiment in the test project."""
    study_dir = tmp_project / "studies" / "test-study"
    study_dir.mkdir(parents=True)
    (study_dir / "README.md").write_text("# Test Study\n")
    (study_dir / "experiments").mkdir()

    exp_dir = study_dir / "experiments" / "test-exp"
    exp_dir.mkdir(parents=True)

    experiment_data = {
        "id": "test-exp",
        "study": "test-study",
        "status": "completed",
        "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": "2025-01-01T01:00:00+00:00",
        "git_sha": "abc123",
        "command": "ox run train.py --experiment test-exp",
        "tags": ["test", "baseline"],
        "tracker_run_id": "run-123",
    }
    (exp_dir / "experiment.json").write_text(json.dumps(experiment_data, indent=2))

    config_data = {"lr": 0.001, "batch_size": 64, "epochs": 20}
    (exp_dir / "config.yaml").write_text(yaml.dump(config_data))

    (exp_dir / "NOTES.md").write_text("# Test Experiment\n\nSome notes.\n")

    return exp_dir


@pytest.fixture
def git_project(tmp_project: Path) -> Path:
    """Create a tmp_project that is also a git repo."""
    subprocess.run(["git", "init"], cwd=tmp_project, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_project, capture_output=True, check=True)
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@test.com", "commit", "-m", "init"],
        cwd=tmp_project,
        capture_output=True,
        check=True,
    )
    return tmp_project
