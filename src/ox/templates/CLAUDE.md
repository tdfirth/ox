# {{PROJECT_NAME}}

## Project Overview

This is a research project managed with [ox](https://github.com/tdfirth/ox), a lightweight experiment framework designed for AI research with Claude Code at the center of the workflow.

## Project Structure

```
{{PROJECT_NAME}}/
├── CLAUDE.md                 # This file — project context for Claude Code
├── .claude/skills/           # Claude skill files for common operations
├── ox.yaml                   # Project configuration
├── studies/                  # Research studies and experiments
│   └── <study-name>/
│       ├── README.md         # Study goals, hypotheses, findings
│       └── experiments/
│           └── <exp-name>/
│               ├── experiment.json  # Machine-readable metadata
│               ├── config.yaml      # Hyperparameters
│               └── NOTES.md         # Observations and results
├── src/
│   └── {{PKG_NAME}}/
│       ├── __init__.py
│       └── scripts/          # Training entrypoints
│           └── train.py      # Example training script
└── .ox/metrics/              # Local tracker output (gitignored)
```

## Key Commands

```bash
# Create a new study
ox new study "study name"

# Create an experiment within a study
ox new experiment <study> <name> --tag <tag>

# See what parameters a training script accepts
ox config-schema src/{{PKG_NAME}}/scripts/train.py

# Run a training script with an experiment
ox run src/{{PKG_NAME}}/scripts/train.py --config <config.yaml> --experiment <exp-id>

# Quick ad-hoc run (no formal experiment tracking)
ox run src/{{PKG_NAME}}/scripts/train.py --lr 0.01 --epochs 5

# List experiments
ox ls
ox ls --study <name> --status completed

# Query experiments with SQL
ox query "status = 'completed' AND lr < 0.001"

# Show experiment details
ox show <experiment-id>

# Check running experiments
ox status
```

## Workflow

### Starting a New Study

1. Create the study: `ox new study "descriptive name"`
2. Edit the study README.md with goals, hypotheses, and background
3. Plan your experiments — what baselines do you need? What ablations?

### Running an Experiment

1. Check git status — ensure all changes are committed (`git status`)
2. If there are uncommitted changes, commit them with a descriptive message
3. Create the experiment: `ox new experiment <study> <name> --tag <tag>`
4. Write config.yaml with the desired hyperparameters
5. Run: `ox run <script> --config <config.yaml> --experiment <exp-id>`
6. After completion, update NOTES.md with observations and results
7. Commit the results: `git add . && git commit -m "Results: <exp-id>"`

### Querying Results

- List all experiments: `ox ls`
- Filter by study: `ox ls --study <name>`
- Filter by status: `ox ls --status completed`
- Complex queries: `ox query "lr < 0.001 AND epochs > 10"`
- Show details: `ox show <experiment-id>`

### Git Discipline

- **Always commit before running an experiment.** The experiment.json records the git SHA for reproducibility.
- Use descriptive commit messages that reference the study/experiment.
- Commit experiment results and notes after analyzing them.
- The git history IS your experiment history.

## Training Scripts

Training scripts live in `src/{{PKG_NAME}}/scripts/`. They follow a simple convention:

1. Define a `Config` class (Pydantic BaseModel) with your hyperparameters
2. Define a `main(config: Config, tracker: Tracker)` function
3. No argparse needed — ox generates CLI flags from the Pydantic model

Example:

```python
from pydantic import BaseModel
from ox import Tracker

class Config(BaseModel):
    lr: float = 1e-3
    batch_size: int = 32
    epochs: int = 10

def main(config: Config, tracker: Tracker) -> None:
    for epoch in range(config.epochs):
        loss = train_one_epoch(model, config)
        tracker.log({"loss": loss, "epoch": epoch}, step=epoch)
```

Use `ox config-schema <script>` to see the full JSON schema of accepted parameters.

## Tracker

Metrics are logged via the Tracker interface. Call `tracker.log({"loss": 0.5}, step=10)`.

The backend is configured in ox.yaml (currently: {{TRACKER_BACKEND}}).

- **local**: Writes JSONL files to `.ox/metrics/`. Good for development.
- **wandb**: Logs to Weights & Biases. Install with `uv add 'ox-ai[wandb]'`.

## Skills

Claude skill files are in `.claude/skills/`. These provide detailed guidance for common operations. Read the relevant skill file before performing complex operations:

- `plan-study.md` — How to plan and scope a research study
- `create-experiment.md` — How to create and configure experiments
- `run-local.md` — How to run experiments locally
- `analyze-results.md` — How to analyze and compare results
- `query-experiments.md` — How to find and filter experiments
- `git-workflow.md` — Git practices for research reproducibility
- `debug-run.md` — How to debug failed experiments
