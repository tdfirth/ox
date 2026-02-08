"""Tracker protocol and backends for logging experiment metrics."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class Tracker(Protocol):
    """Protocol for experiment metric tracking backends."""

    def init_run(self, run_id: str, config: dict[str, Any]) -> None:
        """Initialize a new tracking run."""
        ...

    def log(self, metrics: dict[str, Any], step: int | None = None) -> None:
        """Log metrics, optionally associated with a step."""
        ...

    def finish(self) -> None:
        """Finalize the tracking run."""
        ...


class LocalTracker:
    """Writes metrics to a local JSONL file."""

    def __init__(self, output_dir: str | Path = ".ox/metrics") -> None:
        self._output_dir = Path(output_dir)
        self._run_id: str | None = None
        self._file: Any = None
        self._total_steps: int = 0

    def init_run(self, run_id: str, config: dict[str, Any]) -> None:
        """Initialize a run, creating the JSONL output file."""
        self._run_id = run_id
        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._output_dir / f"{run_id}_metrics.jsonl"
        self._file = open(path, "a")  # noqa: SIM115
        self._write({"type": "config", "run_id": run_id, "config": config})
        logger.info("LocalTracker logging to %s", path)

    def log(self, metrics: dict[str, Any], step: int | None = None) -> None:
        """Log metrics to the JSONL file."""
        entry: dict[str, Any] = {
            "type": "metrics",
            "timestamp": _now_iso(),
        }
        if step is not None:
            entry["step"] = step
            self._total_steps = max(self._total_steps, step)
        entry.update(metrics)
        self._write(entry)

    def finish(self) -> None:
        """Write a finish entry and close the file."""
        if self._file is not None:
            self._write(
                {
                    "type": "finish",
                    "run_id": self._run_id,
                    "timestamp": _now_iso(),
                    "total_steps": self._total_steps,
                }
            )
            self._file.close()
            self._file = None

    def _write(self, entry: dict[str, Any]) -> None:
        if self._file is not None:
            self._file.write(json.dumps(entry) + "\n")
            self._file.flush()


class WandbTracker:
    """Wraps the wandb SDK for metric tracking."""

    def __init__(
        self,
        project: str | None = None,
        entity: str | None = None,
    ) -> None:
        self._project = project
        self._entity = entity
        self._run: Any = None

    def init_run(self, run_id: str, config: dict[str, Any]) -> None:
        """Initialize a wandb run."""
        try:
            import wandb
        except ImportError:
            raise ImportError(
                "wandb is required for WandbTracker. Install it with: uv add 'ox-ai[wandb]'"
            ) from None

        self._run = wandb.init(
            id=run_id,
            project=self._project,
            entity=self._entity,
            config=config,
        )

    def log(self, metrics: dict[str, Any], step: int | None = None) -> None:
        """Log metrics to wandb."""
        if self._run is not None:
            self._run.log(metrics, step=step)

    def finish(self) -> None:
        """Finish the wandb run."""
        if self._run is not None:
            self._run.finish()
            self._run = None


def get_tracker(config: dict[str, Any] | None = None) -> Tracker:
    """Create a tracker instance from ox.yaml configuration.

    Args:
        config: Optional tracker config dict. If not provided, reads from ox.yaml.

    Returns:
        An initialized Tracker instance.
    """
    if config is None:
        import yaml

        from ox.experiments import find_project_root

        root = find_project_root()
        ox_yaml = root / "ox.yaml"
        if not ox_yaml.exists():
            logger.warning("No ox.yaml found, using LocalTracker with defaults")
            return LocalTracker()
        with open(ox_yaml) as f:
            project_config = yaml.safe_load(f)
        config = project_config.get("tracker", {})

    backend = config.get("backend", "local")

    if backend == "local":
        output_dir = config.get("output_dir", ".ox/metrics")
        return LocalTracker(output_dir=output_dir)
    elif backend == "wandb":
        return WandbTracker(
            project=config.get("project"),
            entity=config.get("entity"),
        )
    else:
        raise ValueError(
            f"Unknown tracker backend: {backend!r}. Supported backends: 'local', 'wandb'"
        )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
