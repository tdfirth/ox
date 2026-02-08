"""Click-based CLI for ox."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import click

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


def _slugify(name: str) -> str:
    """Lowercase, replace spaces and special chars with hyphens."""
    return name.lower().replace(" ", "-").replace("_", "-")


def _pkg_name(name: str) -> str:
    """Convert a project name to a valid Python package name."""
    return _slugify(name).replace("-", "_")


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """ox — lightweight experiment management for AI research."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        root = find_project_root()
    except FileNotFoundError:
        click.echo("ox — lightweight experiment management for AI research")
        click.echo()
        click.echo("Not inside an ox project. Run 'ox init <name>' to create one.")
        click.echo("Run 'ox --help' for all commands.")
        return

    import yaml

    ox_yaml = root / "ox.yaml"
    project_name = root.name
    if ox_yaml.exists():
        with open(ox_yaml) as f:
            config = yaml.safe_load(f)
        if config and config.get("project", {}).get("name"):
            project_name = config["project"]["name"]

    experiments = load_all_experiments(root)
    studies = {e.study for e in experiments}
    by_status = {}
    for exp in experiments:
        by_status[exp.status.value] = by_status.get(exp.status.value, 0) + 1

    click.echo(f"ox — {project_name}")
    click.echo(f"  root: {root}")
    click.echo(f"  studies: {len(studies)}")
    click.echo(f"  experiments: {len(experiments)}")
    if by_status:
        summary = ", ".join(f"{v} {k}" for k, v in sorted(by_status.items()))
        click.echo(f"  ({summary})")
    else:
        click.echo()
        click.echo("No experiments yet. Get started:")
        click.echo('  ox new study "my study"')
        click.echo("  ox new experiment my-study baseline")


@cli.command()
@click.argument("name")
def init(name: str) -> None:
    """Scaffold a new research project."""
    slug = _slugify(name)
    pkg = _pkg_name(name)
    project_dir = Path.cwd() / slug

    if project_dir.exists():
        raise click.ClickException(f"Directory already exists: {project_dir}")

    click.echo(f"Creating project: {slug}")

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

    click.echo(f"Project created at {project_dir}")
    click.echo(f"  cd {slug} && uv sync")


@cli.group()
def new() -> None:
    """Create new studies or experiments."""


@new.command("study")
@click.argument("name")
def new_study(name: str) -> None:
    """Create a new study directory."""
    root = find_project_root()
    slug = _slugify(name)
    study_dir = root / "studies" / slug

    if study_dir.exists():
        raise click.ClickException(f"Study already exists: {slug}")

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

    click.echo(f"Created study: {slug}")
    click.echo(f"  Edit {readme.relative_to(root)} to add goals and hypotheses")


@new.command("experiment")
@click.argument("study")
@click.argument("name")
@click.option("--tag", "-t", multiple=True, help="Tags for the experiment")
def new_experiment(study: str, name: str, tag: tuple[str, ...]) -> None:
    """Create a new experiment in a study."""
    root = find_project_root()
    study_slug = _slugify(study)
    exp_slug = _slugify(name)

    study_dir = root / "studies" / study_slug
    if not study_dir.exists():
        raise click.ClickException(
            f'Study not found: {study_slug}\nCreate it first with: ox new study "{study}"'
        )

    exp_dir = study_dir / "experiments" / exp_slug
    if exp_dir.exists():
        raise click.ClickException(f"Experiment already exists: {exp_slug}")

    exp_dir.mkdir(parents=True)

    ts = now_iso()
    experiment = Experiment(
        id=exp_slug,
        study=study_slug,
        status=Status.CREATED,
        created_at=ts,
        updated_at=ts,
        git_sha=get_current_git_sha(),
        tags=list(tag),
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

    click.echo(f"Created experiment: {study_slug}/{exp_slug}")
    click.echo(f"  Edit config: {(exp_dir / 'config.yaml').relative_to(root)}")


@cli.command()
@click.argument("script")
@click.option("--config", "config_path", type=click.Path(exists=True), help="YAML config file")
@click.option("--experiment", "experiment_id", help="Experiment ID to track")
@click.argument("overrides", nargs=-1, type=click.UNPROCESSED)
def run(
    script: str,
    config_path: str | None,
    experiment_id: str | None,
    overrides: tuple[str, ...],
) -> None:
    """Run a training script."""
    in_project = True
    try:
        find_project_root()
    except FileNotFoundError:
        in_project = False
        click.echo(
            "Warning: not inside an ox project (no ox.yaml found).\n"
            "Tracker will use defaults. If your script has dependencies\n"
            "not installed in the current environment, this may fail.\n"
            "Consider running from within your project with 'oxen-team'\n"
            "as a dependency, or run 'ox init <name>' to create a project.\n",
            err=True,
        )

    config_cls, main_fn = discover_entry(script)

    cli_overrides = parse_cli_overrides(list(overrides), config_cls) if overrides else {}
    config = load_config(config_cls, config_path=config_path, overrides=cli_overrides)

    exp: Experiment | None = None
    exp_path: Path | None = None

    if experiment_id:
        if not in_project:
            raise click.ClickException(
                "Cannot use --experiment outside an ox project.\n"
                "Run from within your project directory."
            )
        try:
            root = find_project_root()
            exp, exp_path = find_experiment(experiment_id, root)
        except FileNotFoundError as e:
            raise click.ClickException(f"Experiment not found: {experiment_id}") from e

        full_command = _build_command_string(script, config_path, experiment_id, overrides)
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
        click.echo("Run completed successfully.")
    except Exception:
        tracker.finish()
        if exp is not None and exp_path is not None:
            exp.status = Status.FAILED
            exp.updated_at = now_iso()
            save_experiment(exp, exp_path)
        raise


@cli.command("ls")
@click.option("--study", help="Filter by study")
@click.option("--status", "status_filter", help="Filter by status")
@click.option("--tag", help="Filter by tag")
def ls_experiments(study: str | None, status_filter: str | None, tag: str | None) -> None:
    """List experiments."""
    try:
        root = find_project_root()
    except FileNotFoundError as e:
        raise click.ClickException(str(e)) from e

    experiments = load_all_experiments(root)

    if study:
        experiments = [e for e in experiments if e.study == _slugify(study)]
    if status_filter:
        experiments = [e for e in experiments if e.status.value == status_filter]
    if tag:
        experiments = [e for e in experiments if tag in e.tags]

    if not experiments:
        click.echo("No experiments found.")
        return

    _print_experiment_table(experiments)


@cli.command()
@click.argument("expression")
def query(expression: str) -> None:
    """Query experiments using a SQL WHERE clause."""
    try:
        root = find_project_root()
        results = query_experiments(expression, root)
    except FileNotFoundError as e:
        raise click.ClickException(str(e)) from e
    except ValueError as e:
        raise click.ClickException(str(e)) from e

    if not results:
        click.echo("No matching experiments.")
        return

    for row in results:
        click.echo(json.dumps(row, indent=2, default=str))


@cli.command()
@click.argument("experiment_id")
def show(experiment_id: str) -> None:
    """Show details of a specific experiment."""
    try:
        root = find_project_root()
        exp, exp_path = find_experiment(experiment_id, root)
    except FileNotFoundError as e:
        raise click.ClickException(str(e)) from e

    click.echo(f"Experiment: {exp.id}")
    click.echo(f"Study:      {exp.study}")
    click.echo(f"Status:     {exp.status.value}")
    click.echo(f"Created:    {exp.created_at}")
    click.echo(f"Updated:    {exp.updated_at}")
    if exp.git_sha:
        click.echo(f"Git SHA:    {exp.git_sha}")
    if exp.command:
        click.echo(f"Command:    {exp.command}")
    if exp.tags:
        click.echo(f"Tags:       {', '.join(exp.tags)}")
    if exp.tracker_run_id:
        click.echo(f"Tracker ID: {exp.tracker_run_id}")

    if exp.config:
        click.echo("\nConfig:")
        for k, v in sorted(exp.config.items()):
            click.echo(f"  {k}: {v}")

    notes_path = exp_path.parent / "NOTES.md"
    if notes_path.exists():
        click.echo(f"\nNotes ({notes_path.relative_to(root)}):")
        click.echo(notes_path.read_text())


@cli.command()
@click.argument("run_id", required=False)
def status(run_id: str | None) -> None:
    """Show running experiments."""
    try:
        root = find_project_root()
    except FileNotFoundError as e:
        raise click.ClickException(str(e)) from e

    experiments = load_all_experiments(root)

    if run_id:
        matches = [e for e in experiments if e.id == run_id]
        if not matches:
            raise click.ClickException(f"Experiment not found: {run_id}")
        exp = matches[0]
        click.echo(f"Experiment: {exp.id}")
        click.echo(f"Status:     {exp.status.value}")
        click.echo(f"Updated:    {exp.updated_at}")
        if exp.command:
            click.echo(f"Command:    {exp.command}")
        return

    running = [e for e in experiments if e.status == Status.RUNNING]
    if not running:
        click.echo("No experiments currently running.")
        return

    _print_experiment_table(running)


@cli.command("config-schema")
@click.argument("script")
def config_schema(script: str) -> None:
    """Print the JSON schema for a script's Config class."""
    try:
        config_cls, _ = discover_entry(script)
    except (FileNotFoundError, ValueError) as e:
        raise click.ClickException(str(e)) from e

    schema = config_cls.model_json_schema()
    click.echo(json.dumps(schema, indent=2))


def _print_experiment_table(experiments: list[Experiment]) -> None:
    """Print experiments in a formatted table."""
    headers = ["ID", "Study", "Status", "Tags", "Updated"]
    rows: list[list[str]] = []
    for exp in experiments:
        rows.append(
            [
                exp.id,
                exp.study,
                exp.status.value,
                ", ".join(exp.tags) if exp.tags else "",
                exp.updated_at[:19],
            ]
        )

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "  ".join("-" * w for w in col_widths)
    click.echo(header_line)
    click.echo(separator)
    for row in rows:
        click.echo("  ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)))


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
