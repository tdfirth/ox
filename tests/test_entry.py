"""Tests for ox.entry — Config/main discovery and config loading."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ox.entry import discover_entry, load_config, parse_cli_overrides


class TestDiscoverEntry:
    def test_discovers_config_and_main(self, tmp_script: Path) -> None:
        config_cls, main_fn = discover_entry(tmp_script)
        assert config_cls.__name__ == "Config"
        assert callable(main_fn)

    def test_config_has_expected_fields(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        fields = config_cls.model_fields
        assert "lr" in fields
        assert "batch_size" in fields
        assert "epochs" in fields

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Script not found"):
            discover_entry(tmp_path / "nonexistent.py")

    def test_raises_on_non_python_file(self, tmp_path: Path) -> None:
        txt = tmp_path / "script.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match=r"Expected a \.py file"):
            discover_entry(txt)

    def test_raises_on_missing_config(self, tmp_path: Path) -> None:
        script = tmp_path / "no_config.py"
        script.write_text("def main(config, tracker): pass\n")
        with pytest.raises(ValueError, match="No Config class found"):
            discover_entry(script)

    def test_raises_on_missing_main(self, tmp_path: Path) -> None:
        script = tmp_path / "no_main.py"
        script.write_text(
            "from pydantic import BaseModel\nclass Config(BaseModel):\n    x: int = 1\n"
        )
        with pytest.raises(ValueError, match="No main function found"):
            discover_entry(script)

    def test_raises_on_script_with_syntax_error(self, tmp_path: Path) -> None:
        script = tmp_path / "bad.py"
        script.write_text("def broken(:\n")
        with pytest.raises(ValueError, match="Error executing script"):
            discover_entry(script)


class TestLoadConfig:
    def test_defaults_only(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        config = load_config(config_cls)
        assert config.lr == 1e-3  # type: ignore[attr-defined]
        assert config.batch_size == 32  # type: ignore[attr-defined]
        assert config.epochs == 10  # type: ignore[attr-defined]

    def test_yaml_overrides_defaults(self, tmp_script: Path, tmp_path: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        yaml_path = tmp_path / "config.yaml"
        yaml_path.write_text(yaml.dump({"lr": 0.01, "epochs": 5}))

        config = load_config(config_cls, config_path=yaml_path)
        assert config.lr == 0.01  # type: ignore[attr-defined]
        assert config.epochs == 5  # type: ignore[attr-defined]
        assert config.batch_size == 32  # type: ignore[attr-defined]

    def test_cli_overrides_yaml(self, tmp_script: Path, tmp_path: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        yaml_path = tmp_path / "config.yaml"
        yaml_path.write_text(yaml.dump({"lr": 0.01, "epochs": 5}))

        config = load_config(config_cls, config_path=yaml_path, overrides={"lr": 0.1})
        assert config.lr == 0.1  # type: ignore[attr-defined]
        assert config.epochs == 5  # type: ignore[attr-defined]

    def test_raises_on_missing_yaml(self, tmp_script: Path, tmp_path: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config(config_cls, config_path=tmp_path / "nope.yaml")

    def test_empty_yaml(self, tmp_script: Path, tmp_path: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        yaml_path = tmp_path / "empty.yaml"
        yaml_path.write_text("")
        config = load_config(config_cls, config_path=yaml_path)
        assert config.lr == 1e-3  # type: ignore[attr-defined]


class TestParseCliOverrides:
    def test_parse_float(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        result = parse_cli_overrides(["--lr", "0.01"], config_cls)
        assert result == {"lr": 0.01}

    def test_parse_int(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        result = parse_cli_overrides(["--epochs", "5"], config_cls)
        assert result == {"epochs": 5}

    def test_parse_string(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        result = parse_cli_overrides(["--name", "experiment1"], config_cls)
        assert result == {"name": "experiment1"}

    def test_parse_bool_true(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        result = parse_cli_overrides(["--debug", "true"], config_cls)
        assert result == {"debug": True}

    def test_parse_bool_flag_only(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        result = parse_cli_overrides(["--debug"], config_cls)
        assert result == {"debug": True}

    def test_hyphens_to_underscores(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        result = parse_cli_overrides(["--batch-size", "16"], config_cls)
        assert result == {"batch_size": 16}

    def test_multiple_overrides(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        result = parse_cli_overrides(["--lr", "0.1", "--epochs", "3"], config_cls)
        assert result == {"lr": 0.1, "epochs": 3}

    def test_raises_on_unknown_field(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        with pytest.raises(ValueError, match="Unknown config field"):
            parse_cli_overrides(["--nonexistent", "val"], config_cls)

    def test_raises_on_missing_value(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        with pytest.raises(ValueError, match="Missing value"):
            parse_cli_overrides(["--lr"], config_cls)

    def test_raises_on_unexpected_arg(self, tmp_script: Path) -> None:
        config_cls, _ = discover_entry(tmp_script)
        with pytest.raises(ValueError, match="Unexpected argument"):
            parse_cli_overrides(["positional"], config_cls)
