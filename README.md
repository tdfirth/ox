# ox

A lightweight framework for managing AI research experiments with Claude Code at the heart of the workflow.

Like a good ox: strong work ethic, no tangles. Think of it as a yak that went to finishing school.

## Install

```bash
uv add ox-ai
```

## Quick Start

```bash
# Create a project
ox init my-research
cd my-research
uv sync

# Create a study
ox new study "learning rate schedules"

# Create an experiment
ox new experiment learning-rate-schedules "cosine-baseline" --tag lr --tag cosine

# Check what a script accepts
ox config-schema src/my_research/scripts/train.py

# Run it
ox run src/my_research/scripts/train.py \
  --config studies/learning-rate-schedules/experiments/cosine-baseline/config.yaml \
  --experiment cosine-baseline

# Query results
ox ls --study learning-rate-schedules
ox query "status = 'completed' ORDER BY updated_at DESC"
ox show cosine-baseline
```

## How It Works

Write a training script with two conventions:

```python
from pydantic import BaseModel
from ox import Tracker

class Config(BaseModel):
    lr: float = 1e-3
    batch_size: int = 32
    epochs: int = 10

def main(config: Config, tracker: Tracker) -> None:
    for epoch in range(config.epochs):
        loss = train_epoch(model, config)
        tracker.log({"loss": loss, "epoch": epoch}, step=epoch)
```

No argparse. No decorators. No registration. The `Config` class is your argument spec — ox generates CLI flags from the Pydantic model automatically.

## Philosophy

- **Get out of the agent's way.** Claude Code is the orchestrator. Ox provides composable primitives.
- **Convention over configuration.** A `Config` class and a `main` function. That's it.
- **Everything in the repo.** Experiments, configs, notes — all in version control.
- **Framework-agnostic.** Use PyTorch, JAX, whatever. Ox handles config and tracking.
- **Skills over scaffolding.** Complex workflows are Claude Code skills, not framework code.

## Project Structure

After `ox init`, you get:

```
my-research/
├── CLAUDE.md                 # Master prompt for Claude Code
├── .claude/skills/           # Claude skill files (yours to customize)
├── ox.yaml                   # Project config
├── studies/                  # Research studies and experiments
├── src/my_research/scripts/  # Training entrypoints
└── .ox/metrics/              # Local tracker output (gitignored)
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `ox init <name>` | Scaffold a new project |
| `ox new study <name>` | Create a study |
| `ox new experiment <study> <name>` | Create an experiment |
| `ox run <script> [--config PATH] [--experiment ID]` | Run a training script |
| `ox ls [--study S] [--status S] [--tag T]` | List experiments |
| `ox query <expression>` | SQL query over experiments |
| `ox show <id>` | Show experiment details |
| `ox status` | Show running experiments |
| `ox config-schema <script>` | Print config JSON schema |

## Tracker

Metrics are logged via the `Tracker` interface:

```python
tracker.log({"loss": 0.5, "acc": 0.9}, step=10)
```

Backends:
- **local** (default) — JSONL files in `.ox/metrics/`
- **wandb** — Weights & Biases (`uv add 'ox-ai[wandb]'`)

Configure in `ox.yaml`:

```yaml
tracker:
  backend: local
  output_dir: .ox/metrics
```

## License

MIT
