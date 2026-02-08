# Git Workflow

Git practices for reproducible research.

## The Core Rule

**Always commit before running an experiment.**

When you create an experiment or run a training script, ox records the current git SHA in experiment.json. This is how you reproduce results — you can always check out exactly the code that produced a specific result.

## Pre-run Workflow

```bash
# 1. Check for uncommitted changes
git status

# 2. Stage and commit
git add -A
git commit -m "Add sparse attention experiment config"

# 3. Now create/run the experiment
ox new experiment sparse-attention "sparse-v1" --tag sparse
ox run src/my_research/scripts/train.py \
  --config studies/sparse-attention/experiments/sparse-v1/config.yaml \
  --experiment sparse-v1
```

## Post-run Workflow

```bash
# After the experiment completes
# 1. Review results
ox show sparse-v1

# 2. Write up observations in NOTES.md
# Edit studies/sparse-attention/experiments/sparse-v1/NOTES.md

# 3. Update study README if there are key findings
# Edit studies/sparse-attention/README.md

# 4. Commit everything
git add -A
git commit -m "Results: sparse-v1 — 35% memory reduction, 2% perplexity increase"
```

## Commit Message Conventions

Use descriptive messages that reference the study/experiment:

```
# Creating experiments
Add baseline experiment config for sparse attention study
Set up lr sweep: 1e-4, 3e-4, 1e-3, 3e-3

# After results
Results: sparse-v1 — 35% memory reduction, 2% perplexity increase
Analysis: lr sweep shows 3e-4 is optimal for 6-layer transformer

# Code changes
Add sparse attention module with top-k selection
Fix gradient clipping in training loop
```

## Reproducing an Experiment

```bash
# Find the git SHA from experiment metadata
ox show my-experiment

# Check out that exact code
git stash  # save current work
git checkout <sha>

# Re-run with the same config
ox run src/my_research/scripts/train.py --config <config.yaml>

# Return to your branch
git checkout main
git stash pop
```

## Branch Strategy

For most research projects, working on `main` is fine. Consider branches when:

- You're making a large architectural change to the training code
- Multiple people are working on the same repo
- You want to try something experimental without affecting the main line

## What to Commit

**Always commit:**
- Training scripts and model code
- Config files (config.yaml)
- Experiment metadata (experiment.json)
- Analysis notes (NOTES.md, study README.md)
- Visualization scripts

**Never commit:**
- Model checkpoints (too large)
- Raw datasets (use data versioning or links)
- Metrics JSONL files (.ox/metrics/ is gitignored)
- Virtual environments

## What Not to Do

- Don't run experiments with uncommitted changes. Results won't be reproducible.
- Don't force-push. You'll lose experiment history.
- Don't amend commits that have experiment results pointing to them.
- Don't rebase experiment history. The git SHAs in experiment.json will become invalid.
