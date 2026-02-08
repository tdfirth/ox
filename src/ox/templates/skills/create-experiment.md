# Create Experiment

Guide for creating and configuring experiments.

## Creating an Experiment

```bash
ox new experiment <study> <name> --tag <tag1> --tag <tag2>
```

This creates:
- `experiment.json` — metadata (status, git SHA, timestamps)
- `config.yaml` — hyperparameters (you fill this in)
- `NOTES.md` — observations template

## Writing config.yaml

The config must match the `Config` class in the training script you'll run. Use `ox config-schema <script>` to see what fields are available.

```bash
# See available parameters
ox config-schema src/my_research/scripts/train.py
```

Example config:

```yaml
lr: 0.001
batch_size: 64
epochs: 20
hidden_dim: 512
num_layers: 4
dataset: "wikitext-103"
```

Only include fields you want to override — any field not in config.yaml will use the default from the `Config` class.

## Choosing Hyperparameters

- **Document your rationale.** Why this learning rate? Add a comment in NOTES.md.
- **Use sensible defaults.** If the script has good defaults, only override what you're testing.
- **Be systematic.** If comparing learning rates, use a geometric progression (1e-4, 3e-4, 1e-3, 3e-3).
- **Check the literature.** What do similar papers use?

## Grid Searches / Sweeps

Ox doesn't have a built-in sweep system. Instead, create multiple experiments:

```bash
ox new experiment my-study "lr-1e4" --tag sweep --tag lr
ox new experiment my-study "lr-3e4" --tag sweep --tag lr
ox new experiment my-study "lr-1e3" --tag sweep --tag lr
ox new experiment my-study "lr-3e3" --tag sweep --tag lr
```

Each gets its own config.yaml with the appropriate value. This is intentional:
- Every run is independently documented
- You can see exactly what was tried
- Each has its own NOTES.md for observations

## Git Workflow

**Always commit before creating an experiment.** The experiment.json records the current git SHA. This is how you ensure reproducibility.

```bash
git add -A
git commit -m "Add training script for sparse attention"
ox new experiment sparse-attention "baseline"
```

See the `git-workflow` skill for more details.

## Naming Conventions

Good experiment names:
- `dense-baseline` — what it is
- `lr-1e3-bs64` — key parameters
- `topk-k32-heads8` — specific variant

Avoid:
- `test1`, `exp2` — not descriptive
- Very long names — they become directory paths

## Tags

Tags help with filtering. Common patterns:
- Method type: `--tag sparse`, `--tag dense`
- Sweep membership: `--tag lr-sweep`
- Stage: `--tag baseline`, `--tag ablation`
- Dataset: `--tag wikitext`, `--tag openwebtext`

Query by tag: `ox ls --tag baseline`
