"""Experiment metadata: read, write, and query."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class Status(StrEnum):
    """Experiment status values."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Experiment:
    """Represents an experiment's metadata."""

    id: str
    study: str
    status: Status
    created_at: str
    updated_at: str
    git_sha: str | None = None
    command: str | None = None
    tags: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    tracker_run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict for JSON storage (excludes config)."""
        return {
            "id": self.id,
            "study": self.study,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "git_sha": self.git_sha,
            "command": self.command,
            "tags": self.tags,
            "tracker_run_id": self.tracker_run_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Experiment:
        """Deserialize from a dict."""
        return cls(
            id=data["id"],
            study=data["study"],
            status=Status(data["status"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            git_sha=data.get("git_sha"),
            command=data.get("command"),
            tags=data.get("tags", []),
            config=data.get("config", {}),
            tracker_run_id=data.get("tracker_run_id"),
        )


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (default: cwd) looking for ox.yaml.

    Args:
        start: Directory to start searching from.

    Returns:
        Path to the project root directory.

    Raises:
        FileNotFoundError: If no ox.yaml is found.
    """
    current = (start or Path.cwd()).resolve()
    while True:
        if (current / "ox.yaml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise FileNotFoundError(
        "Could not find ox.yaml in any parent directory.\n"
        "Are you in an ox project? Run 'ox init <name>' to create one."
    )


def find_all_experiments(root: Path | None = None) -> list[Path]:
    """Find all experiment.json files under studies/.

    Args:
        root: Project root directory. Discovered from cwd if not provided.

    Returns:
        List of paths to experiment.json files.
    """
    if root is None:
        root = find_project_root()
    studies_dir = root / "studies"
    if not studies_dir.exists():
        return []
    return sorted(studies_dir.glob("**/experiment.json"))


def load_experiment(path: Path) -> Experiment:
    """Load an experiment from an experiment.json file.

    Also loads config.yaml from the same directory if it exists.

    Args:
        path: Path to the experiment.json file.

    Returns:
        An Experiment instance.
    """
    with open(path) as f:
        data = json.load(f)

    config_path = path.parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
        if config is not None:
            data["config"] = config

    return Experiment.from_dict(data)


def save_experiment(experiment: Experiment, path: Path) -> None:
    """Write experiment.json to disk.

    Args:
        experiment: The experiment to save.
        path: Path to write the experiment.json file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(experiment.to_dict(), f, indent=2)
        f.write("\n")


def load_all_experiments(root: Path | None = None) -> list[Experiment]:
    """Load all experiments, skipping malformed ones with warnings.

    Args:
        root: Project root directory.

    Returns:
        List of successfully loaded experiments.
    """
    experiments = []
    for path in find_all_experiments(root):
        try:
            experiments.append(load_experiment(path))
        except Exception as e:
            logger.warning("Skipping malformed experiment at %s: %s", path, e)
    return experiments


def find_experiment(experiment_id: str, root: Path | None = None) -> tuple[Experiment, Path]:
    """Find an experiment by its ID across all studies.

    Args:
        experiment_id: The experiment slug/ID to find.
        root: Project root directory.

    Returns:
        Tuple of (Experiment, path to experiment.json).

    Raises:
        FileNotFoundError: If the experiment is not found.
    """
    if root is None:
        root = find_project_root()

    for path in find_all_experiments(root):
        try:
            exp = load_experiment(path)
            if exp.id == experiment_id:
                return exp, path
        except Exception:
            continue

    raise FileNotFoundError(
        f"Experiment not found: {experiment_id!r}.\nUse 'ox ls' to see available experiments."
    )


def query_experiments(expression: str, root: Path | None = None) -> list[dict[str, Any]]:
    """Query experiments using a SQL WHERE clause, powered by DuckDB.

    Config fields are flattened to top-level columns.

    Args:
        expression: A SQL WHERE clause expression.
        root: Project root directory.

    Returns:
        List of matching experiment dicts.
    """
    import duckdb

    experiments = load_all_experiments(root)
    if not experiments:
        return []

    rows = []
    for exp in experiments:
        row: dict[str, Any] = {
            "id": exp.id,
            "study": exp.study,
            "status": exp.status.value,
            "created_at": exp.created_at,
            "updated_at": exp.updated_at,
            "git_sha": exp.git_sha,
            "command": exp.command,
            "tags": exp.tags,
            "tracker_run_id": exp.tracker_run_id,
        }
        for k, v in exp.config.items():
            if k not in row:
                row[k] = v
        rows.append(row)

    all_keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    for row in rows:
        for k in all_keys:
            row.setdefault(k, None)

    con = duckdb.connect(":memory:")

    columns_sql = ", ".join(f'"{k}" {_duckdb_type(rows[0][k])}' for k in all_keys)
    con.execute(f"CREATE TABLE experiments ({columns_sql})")

    placeholders = ", ".join("?" for _ in all_keys)
    for row in rows:
        values = [_serialize_for_duckdb(row[k]) for k in all_keys]
        con.execute(f"INSERT INTO experiments VALUES ({placeholders})", values)

    try:
        result = con.execute(f"SELECT * FROM experiments WHERE {expression}").fetchall()
        col_names = [desc[0] for desc in con.description]
        return [dict(zip(col_names, r, strict=True)) for r in result]
    except duckdb.Error as e:
        raise ValueError(
            f"Query error: {e}\n"
            f"Expression: {expression}\n"
            f"Available columns: {', '.join(sorted(all_keys))}"
        ) from e
    finally:
        con.close()


def _duckdb_type(value: Any) -> str:
    """Infer a DuckDB column type from a Python value."""
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "BIGINT"
    if isinstance(value, float):
        return "DOUBLE"
    if isinstance(value, list):
        return "VARCHAR"
    return "VARCHAR"


def _serialize_for_duckdb(value: Any) -> Any:
    """Convert Python values to DuckDB-compatible types."""
    if isinstance(value, list):
        return json.dumps(value)
    return value


def get_current_git_sha() -> str | None:
    """Get the current git HEAD SHA.

    Returns:
        The SHA string, or None if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def has_uncommitted_changes() -> bool:
    """Check if the git working tree has uncommitted changes.

    Returns:
        True if there are uncommitted changes.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def now_iso() -> str:
    """Current UTC time in ISO format."""
    return datetime.now(UTC).isoformat()
