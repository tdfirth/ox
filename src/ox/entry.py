"""Convention-based Config/main discovery and config loading."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


def discover_entry(script_path: str | Path) -> tuple[type[BaseModel], Callable]:
    """Load a Python script and discover its Config class and main function.

    Looks for a class named 'Config' that subclasses pydantic.BaseModel
    and a callable named 'main'.

    Args:
        script_path: Path to the Python training script.

    Returns:
        A tuple of (ConfigClass, main_function).

    Raises:
        FileNotFoundError: If the script doesn't exist.
        ValueError: If Config or main cannot be found.
    """
    path = Path(script_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Script not found: {path}")
    if not path.suffix == ".py":
        raise ValueError(f"Expected a .py file, got: {path}")

    module_name = f"_ox_script_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load module from: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise ValueError(f"Error executing script {path}: {e}") from e
    finally:
        sys.modules.pop(module_name, None)

    config_cls = None
    for name, obj in vars(module).items():
        if (
            name == "Config"
            and isinstance(obj, type)
            and issubclass(obj, BaseModel)
            and obj is not BaseModel
        ):
            config_cls = obj
            break

    if config_cls is None:
        raise ValueError(
            f"No Config class found in {path}.\n"
            f"Expected a class named 'Config' that subclasses pydantic.BaseModel:\n\n"
            f"    from pydantic import BaseModel\n\n"
            f"    class Config(BaseModel):\n"
            f"        lr: float = 1e-3\n"
            f"        epochs: int = 10\n"
        )

    main_fn = getattr(module, "main", None)
    if main_fn is None or not callable(main_fn):
        raise ValueError(
            f"No main function found in {path}.\n"
            f"Expected a function named 'main' with signature:\n\n"
            f"    def main(config: Config, tracker: Tracker):\n"
            f"        ...\n"
        )

    return config_cls, main_fn


def load_config(
    config_cls: type[BaseModel],
    config_path: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> BaseModel:
    """Load config with priority: CLI overrides > YAML file > class defaults.

    Args:
        config_cls: The Pydantic model class to instantiate.
        config_path: Optional path to a YAML config file.
        overrides: Optional dict of field overrides from CLI.

    Returns:
        A validated instance of config_cls.
    """
    base: dict[str, Any] = {}

    if config_path is not None:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path) as f:
            loaded = yaml.safe_load(f)
        if loaded is not None:
            base = loaded

    if overrides:
        base.update(overrides)

    return config_cls(**base)


def parse_cli_overrides(args: list[str], config_cls: type[BaseModel]) -> dict[str, Any]:
    """Parse --key value pairs from CLI arguments using the Pydantic schema for type casting.

    Supports: int, float, str, bool. Hyphens and underscores in flag names are
    interchangeable (--learning-rate matches learning_rate field).

    Args:
        args: List of CLI arguments like ['--lr', '0.01', '--epochs', '5'].
        config_cls: The Pydantic model class for type information.

    Returns:
        Dict of parsed overrides.

    Raises:
        ValueError: If an argument is malformed or a flag is not recognized.
    """
    schema = config_cls.model_json_schema()
    properties = schema.get("properties", {})

    field_types: dict[str, str] = {}
    for field_name, field_info in properties.items():
        field_type = field_info.get("type", "string")
        field_types[field_name] = field_type

    overrides: dict[str, Any] = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if not arg.startswith("--"):
            raise ValueError(
                f"Unexpected argument: {arg!r}. Override arguments must be in --key value format."
            )

        key = arg[2:].replace("-", "_")

        if key not in field_types:
            raise ValueError(
                f"Unknown config field: {key!r}. "
                f"Available fields: {', '.join(sorted(field_types.keys()))}"
            )

        field_type = field_types[key]

        if field_type == "boolean":
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                i += 1
                overrides[key] = _parse_bool(args[i], key)
            else:
                overrides[key] = True
        else:
            if i + 1 >= len(args):
                raise ValueError(f"Missing value for argument: --{key}")
            i += 1
            overrides[key] = _cast_value(args[i], field_type, key)

        i += 1

    return overrides


def _parse_bool(value: str, field_name: str) -> bool:
    lower = value.lower()
    if lower in ("true", "1", "yes"):
        return True
    if lower in ("false", "0", "no"):
        return False
    raise ValueError(
        f"Invalid boolean value for --{field_name}: {value!r}. Expected: true/false, yes/no, 1/0"
    )


def _cast_value(value: str, field_type: str, field_name: str) -> Any:
    try:
        if field_type == "integer":
            return int(value)
        elif field_type == "number":
            return float(value)
        else:
            return value
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid value for --{field_name}: {value!r} (expected {field_type})"
        ) from e
