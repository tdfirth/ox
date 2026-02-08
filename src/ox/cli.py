"""Typer-based CLI for ox."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.table import Table

from ox.entry import discover_entry, load_config, parse_cli_overrides
from ox.experiments import (
    Experiment,
    Status,
    find_experiment,
    find_project_root,
    get_current_git_sha,
    load_all_experiments,
    now_iso,
    query_experiments,
    save_experiment,
)
from ox.tracker import get_tracker

TEMPLATES_DIR = Path(__file__).parent / "templates"

cli = typer.Typer(
    help="ox — lightweight experiment management for AI research.",
    no_args_is_help=False,
)
new_cli = typer.Typer(help="Create new studies or experiments.")
cli.add_typer(new_cli, name="new")


def _fail(message: str) -> NoReturn:
    """Print error and exit."""
    print(f"Error: {message}", file=sys.stderr)
    raise typer.Exit(code=1)


def _slugify(name: str) -> str:
    """Lowercase, replace spaces and special chars with hyphens."""
    return name.lower().replace(" ", "-").replace("_", "-")


def _pkg_name(name: str) -> str:
    """Convert a project name to a valid Python package name."""
    return _slugify(name).replace("-", "_")


@cli.callback(invoke_without_command=True)
def root(ctx: typer.Context) -> None:
    """ox — lightweight experiment management for AI research."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        root_path = find_project_root()
    except FileNotFoundError:
        print("ox — lightweight experiment management for AI research")
        print()
        print("Not inside an ox project. Run 'ox init <name>' to create one.")
        print("Run 'ox --help' for all commands.")
        return

    import yaml

    ox_yaml = root_path / "ox.yaml"
    project_name = root_path.name
    if ox_yaml.exists():
        with open(ox_yaml) as f:
            config = yaml.safe_load(f)
        if config and config.get("project", {}).get("name"):
            project_name = config["project"]["name"]

    experiments = load_all_experiments(root_path)
    studies = {e.study for e in experiments}
    by_status: dict[str, int] = {}
    for exp in experiments:
        by_status[exp.status.value] = by_status.get(exp.status.value, 0) + 1

    print(f"ox — {project_name}")
    print(f"  root: {root_path}")
    print(f"  studies: {len(studies)}")
    print(f"  experiments: {len(experiments)}")
    if by_status:
        summary = ", ".join(f"{v} {k}" for k, v in sorted(by_status.items()))
        print(f"  ({summary})")
    else:
        print()
        print("No experiments yet. Get started:")
        print('  ox new study "my study"')
        print("  ox new experiment my-study baseline")


@cli.command()
def init(name: str) -> None:
    """Scaffold a new research project."""
    slug = _slugify(name)
    pkg = _pkg_name(name)
    project_dir = Path.cwd() / slug

    if project_dir.exists():
        _fail(f"Directory already exists: {project_dir}")

    print(f"Creating project: {slug}")

    project_dir.mkdir()
    (project_dir / "studies").mkdir()
    (project_dir / ".ox" / "metrics").mkdir(parents=True)

    src_dir = project_dir / "src" / pkg
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text("")
    scripts_dir = src_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "__init__.py").write_text("")

    train_example = scripts_dir / "train.py"
    train_example.write_text(
        f'"""Example training script for {name}."""\n'
        "\n"
        "from pydantic import BaseModel\n"
        "\n"
        "from ox import Tracker\n"
        "\n"
        "\n"
        "class Config(BaseModel):\n"
        "    lr: float = 1e-3\n"
        "    batch_size: int = 32\n"
        "    epochs: int = 10\n"
        "\n"
        "\n"
        "def main(config: Config, tracker: Tracker) -> None:\n"
        "    for epoch in range(config.epochs):\n"
        "        loss = 1.0 / (epoch + 1)  # placeholder\n"
        '        tracker.log({"loss": loss, "epoch": epoch}, step=epoch)\n'
        '        print(f"epoch {epoch}: loss={loss:.4f}")\n'
        '    tracker.log({"final_loss": loss})\n'
    )

    _render_template("ox.yaml", project_dir / "ox.yaml", PROJECT_NAME=name)

    claude_dir = project_dir / ".claude" / "skills"
    claude_dir.mkdir(parents=True)
    _render_template(
        "CLAUDE.md",
        project_dir / "CLAUDE.md",
        PROJECT_NAME=name,
        PKG_NAME=pkg,
        TRACKER_BACKEND="local",
    )

    skills_src = TEMPLATES_DIR / "skills"
    if skills_src.exists():
        for skill_file in skills_src.glob("*.md"):
            shutil.copy2(skill_file, claude_dir / skill_file.name)

    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text(
        f"[project]\n"
        f'name = "{slug}"\n'
        f'version = "0.1.0"\n'
        f'description = ""\n'
        f'requires-python = ">=3.11"\n'
        f"dependencies = [\n"
        f'    "oxen-team",\n'
        f"]\n"
        f"\n"
        f"[build-system]\n"
        f'requires = ["hatchling"]\n'
        f'build-backend = "hatchling.build"\n'
        f"\n"
        f"[tool.hatch.build.targets.wheel]\n"
        f'packages = ["src/{pkg}"]\n'
    )

    gitignore = project_dir / ".gitignore"
    gitignore.write_text("__pycache__/\n*.py[oc]\nbuild/\ndist/\n*.egg-info\n.venv\n.ox/metrics/\n")

    subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial project scaffold from ox init"],
        cwd=project_dir,
        capture_output=True,
        check=True,
    )

    print(f"Project created at {project_dir}")
    print(f"  cd {slug} && uv sync")


@new_cli.command("study")
def new_study(name: str) -> None:
    """Create a new study directory."""
    root_path = find_project_root()
    slug = _slugify(name)
    study_dir = root_path / "studies" / slug

    if study_dir.exists():
        _fail(f"Study already exists: {slug}")

    study_dir.mkdir(parents=True)
    (study_dir / "experiments").mkdir()

    readme = study_dir / "README.md"
    readme.write_text(
        f"# {name}\n"
        f"\n"
        f"## Goals\n"
        f"\n"
        f"<!-- What are you trying to learn or achieve? -->\n"
        f"\n"
        f"## Hypotheses\n"
        f"\n"
        f"<!-- What do you expect to find? -->\n"
        f"\n"
        f"## Background\n"
        f"\n"
        f"<!-- Relevant context, prior work, references -->\n"
        f"\n"
        f"## Key Findings\n"
        f"\n"
        f"<!-- Updated as experiments complete -->\n"
    )

    print(f"Created study: {slug}")
    print(f"  Edit {readme.relative_to(root_path)} to add goals and hypotheses")


@new_cli.command("experiment")
def new_experiment(
    study: str,
    name: str,
    tag: Annotated[list[str] | None, typer.Option("-t", "--tag")] = None,
) -> None:
    """Create a new experiment in a study."""
    root_path = find_project_root()
    study_slug = _slugify(study)
    exp_slug = _slugify(name)
    tags = tag or []

    study_dir = root_path / "studies" / study_slug
    if not study_dir.exists():
        _fail(f'Study not found: {study_slug}\nCreate it first with: ox new study "{study}"')

    exp_dir = study_dir / "experiments" / exp_slug
    if exp_dir.exists():
        _fail(f"Experiment already exists: {exp_slug}")

    exp_dir.mkdir(parents=True)

    ts = now_iso()
    experiment = Experiment(
        id=exp_slug,
        study=study_slug,
        status=Status.CREATED,
        created_at=ts,
        updated_at=ts,
        git_sha=get_current_git_sha(),
        tags=tags,
    )
    save_experiment(experiment, exp_dir / "experiment.json")

    (exp_dir / "config.yaml").write_text("# Experiment configuration\n")

    (exp_dir / "NOTES.md").write_text(
        f"# {name}\n"
        f"\n"
        f"## Setup\n"
        f"\n"
        f"<!-- Describe what this experiment tests -->\n"
        f"\n"
        f"## Observations\n"
        f"\n"
        f"<!-- Notes during and after the run -->\n"
        f"\n"
        f"## Results\n"
        f"\n"
        f"<!-- Key metrics and outcomes -->\n"
    )

    print(f"Created experiment: {study_slug}/{exp_slug}")
    print(f"  Edit config: {(exp_dir / 'config.yaml').relative_to(root_path)}")


@cli.command(context_settings={"allow_extra_args": True})
def run(
    ctx: typer.Context,
    script: str,
    config_path: Annotated[str | None, typer.Option("--config", help="YAML config file")] = None,
    experiment_id: Annotated[
        str | None, typer.Option("--experiment", help="Experiment ID to track")
    ] = None,
) -> None:
    """Run a training script."""
    in_project = True
    try:
        find_project_root()
    except FileNotFoundError:
        in_project = False
        print(
            "Warning: not inside an ox project (no ox.yaml found).\n"
            "Tracker will use defaults. If your script has dependencies\n"
            "not installed in the current environment, this may fail.\n"
            "Consider running from within your project with 'oxen-team'\n"
            "as a dependency, or run 'ox init <name>' to create a project.",
            file=sys.stderr,
        )

    config_cls, main_fn = discover_entry(script)

    overrides = [a for a in ctx.args if a != "--"]
    cli_overrides = parse_cli_overrides(overrides, config_cls) if overrides else {}
    config = load_config(config_cls, config_path=config_path, overrides=cli_overrides)

    exp: Experiment | None = None
    exp_path: Path | None = None

    if experiment_id:
        if not in_project:
            _fail(
                "Cannot use --experiment outside an ox project.\n"
                "Run from within your project directory."
            )
        try:
            root_path = find_project_root()
            exp, exp_path = find_experiment(experiment_id, root_path)
        except FileNotFoundError:
            _fail(f"Experiment not found: {experiment_id}")

        full_command = _build_command_string(script, config_path, experiment_id, tuple(overrides))
        exp.status = Status.RUNNING
        exp.git_sha = get_current_git_sha()
        exp.command = full_command
        exp.updated_at = now_iso()
        save_experiment(exp, exp_path)

    tracker = get_tracker()
    run_id = experiment_id or f"run-{now_iso().replace(':', '-').replace('+', '')}"
    tracker.init_run(run_id, config.model_dump())

    if exp is not None:
        exp.tracker_run_id = run_id
        save_experiment(exp, exp_path)  # type: ignore[arg-type]

    try:
        main_fn(config, tracker)
        tracker.finish()
        if exp is not None and exp_path is not None:
            exp.status = Status.COMPLETED
            exp.updated_at = now_iso()
            save_experiment(exp, exp_path)
        print("Run completed successfully.")
    except Exception:
        tracker.finish()
        if exp is not None and exp_path is not None:
            exp.status = Status.FAILED
            exp.updated_at = now_iso()
            save_experiment(exp, exp_path)
        raise


@cli.command("ls")
def ls_experiments(
    study: Annotated[str | None, typer.Option(help="Filter by study")] = None,
    status: Annotated[str | None, typer.Option("--status", help="Filter by status")] = None,
    tag: Annotated[str | None, typer.Option(help="Filter by tag")] = None,
) -> None:
    """List experiments."""
    try:
        root_path = find_project_root()
    except FileNotFoundError as e:
        _fail(str(e))

    experiments = load_all_experiments(root_path)

    if study:
        experiments = [exp for exp in experiments if exp.study == _slugify(study)]
    if status:
        experiments = [exp for exp in experiments if exp.status.value == status]
    if tag:
        experiments = [exp for exp in experiments if tag in exp.tags]

    if not experiments:
        print("No experiments found.")
        return

    _print_experiment_table(experiments)


@cli.command()
def query(expression: str) -> None:
    """Query experiments using a SQL WHERE clause."""
    try:
        root_path = find_project_root()
        results = query_experiments(expression, root_path)
    except FileNotFoundError as e:
        _fail(str(e))
    except ValueError as e:
        _fail(str(e))

    if not results:
        print("No matching experiments.")
        return

    for row in results:
        print(json.dumps(row, indent=2, default=str))


@cli.command()
def show(experiment_id: str) -> None:
    """Show details of a specific experiment."""
    try:
        root_path = find_project_root()
        exp, exp_path = find_experiment(experiment_id, root_path)
    except FileNotFoundError as e:
        _fail(str(e))

    print(f"Experiment: {exp.id}")
    print(f"Study:      {exp.study}")
    print(f"Status:     {exp.status.value}")
    print(f"Created:    {exp.created_at}")
    print(f"Updated:    {exp.updated_at}")
    if exp.git_sha:
        print(f"Git SHA:    {exp.git_sha}")
    if exp.command:
        print(f"Command:    {exp.command}")
    if exp.tags:
        print(f"Tags:       {', '.join(exp.tags)}")
    if exp.tracker_run_id:
        print(f"Tracker ID: {exp.tracker_run_id}")

    if exp.config:
        print("\nConfig:")
        for k, v in sorted(exp.config.items()):
            print(f"  {k}: {v}")

    notes_path = exp_path.parent / "NOTES.md"
    if notes_path.exists():
        print(f"\nNotes ({notes_path.relative_to(root_path)}):")
        print(notes_path.read_text())


@cli.command()
def status(run_id: Annotated[str | None, typer.Argument()] = None) -> None:
    """Show running experiments."""
    try:
        root_path = find_project_root()
    except FileNotFoundError as e:
        _fail(str(e))

    experiments = load_all_experiments(root_path)

    if run_id:
        matches = [exp for exp in experiments if exp.id == run_id]
        if not matches:
            _fail(f"Experiment not found: {run_id}")
        exp = matches[0]
        print(f"Experiment: {exp.id}")
        print(f"Status:     {exp.status.value}")
        print(f"Updated:    {exp.updated_at}")
        if exp.command:
            print(f"Command:    {exp.command}")
        return

    running = [exp for exp in experiments if exp.status == Status.RUNNING]
    if not running:
        print("No experiments currently running.")
        return

    _print_experiment_table(running)


@cli.command("config-schema")
def config_schema(script: str) -> None:
    """Print the JSON schema for a script's Config class."""
    try:
        config_cls, _ = discover_entry(script)
    except (FileNotFoundError, ValueError) as e:
        _fail(str(e))

    schema = config_cls.model_json_schema()
    print(json.dumps(schema, indent=2))


def _print_experiment_table(experiments: list[Experiment]) -> None:
    """Print experiments using a Rich table."""
    from rich.console import Console

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID")
    table.add_column("Study")
    table.add_column("Status")
    table.add_column("Tags")
    table.add_column("Updated")

    for exp in experiments:
        table.add_row(
            exp.id,
            exp.study,
            exp.status.value,
            ", ".join(exp.tags) if exp.tags else "",
            exp.updated_at[:19],
        )

    Console().print(table)


def _build_command_string(
    script: str,
    config_path: str | None,
    experiment_id: str | None,
    overrides: tuple[str, ...],
) -> str:
    parts = ["ox", "run", script]
    if config_path:
        parts.extend(["--config", config_path])
    if experiment_id:
        parts.extend(["--experiment", experiment_id])
    if overrides:
        parts.append("--")
        parts.extend(overrides)
    return " ".join(parts)


def _render_template(template_name: str, dest: Path, **kwargs: str) -> None:
    """Render a template file with placeholder substitution."""
    src = TEMPLATES_DIR / template_name
    if not src.exists():
        return
    content = src.read_text()
    for key, value in kwargs.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    dest.write_text(content)
