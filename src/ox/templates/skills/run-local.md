# Run Local

Guide for running experiments on the local machine.

## Basic Run

```bash
# With a formal experiment
ox run src/my_research/scripts/train.py \
  --config studies/my-study/experiments/my-exp/config.yaml \
  --experiment my-exp

# Quick ad-hoc run (no experiment tracking)
ox run src/my_research/scripts/train.py --lr 0.01 --epochs 2
```

## What `ox run` Does

1. Discovers `Config` and `main` from the script
2. Loads config: CLI overrides > YAML file > class defaults
3. If `--experiment` given: updates experiment status to "running"
4. Initializes tracker
5. Calls `main(config, tracker)`
6. On completion: updates status to "completed" or "failed"

## Running in Background

For long runs, use standard Unix tools:

```bash
# Using nohup
nohup ox run src/my_research/scripts/train.py \
  --config config.yaml --experiment my-exp > run.log 2>&1 &
echo $!  # save the PID

# Using tmux
tmux new-session -d -s training 'ox run src/my_research/scripts/train.py --config config.yaml --experiment my-exp'
tmux attach -t training  # to watch
# Ctrl-b d to detach
```

## Monitoring a Run

```bash
# Check experiment status
ox status

# Tail the metrics file (local tracker)
tail -f .ox/metrics/<run-id>_metrics.jsonl

# Watch GPU usage
watch -n 1 nvidia-smi
```

## Running Multiple Experiments

Run sequentially:

```bash
for exp in lr-1e4 lr-3e4 lr-1e3; do
  ox run src/my_research/scripts/train.py \
    --config "studies/my-study/experiments/$exp/config.yaml" \
    --experiment "$exp"
done
```

Run in parallel (if you have the GPU memory):

```bash
CUDA_VISIBLE_DEVICES=0 ox run script.py --config config1.yaml --experiment exp1 &
CUDA_VISIBLE_DEVICES=1 ox run script.py --config config2.yaml --experiment exp2 &
wait
```

## GPU Management

```bash
# See available GPUs
nvidia-smi

# Use a specific GPU
CUDA_VISIBLE_DEVICES=0 ox run script.py --config config.yaml

# Use multiple GPUs
CUDA_VISIBLE_DEVICES=0,1 ox run script.py --config config.yaml
```

## Handling Failures

If a run fails:
1. Check the error: the traceback will be printed
2. The experiment status is automatically set to "failed"
3. Fix the issue
4. Re-run with the same command — it will update the experiment status back to "running"

Common failures:
- **OOM**: Reduce batch size, use gradient accumulation, or use a smaller model
- **NaN loss**: Lower learning rate, check data preprocessing, add gradient clipping
- **Import errors**: Check your virtual environment (`uv sync`)
- **Config errors**: Verify config.yaml matches the script's Config class (`ox config-schema`)

## Pre-run Checklist

1. Is everything committed? (`git status`)
2. Is the config correct? (`ox config-schema` + review config.yaml)
3. Is the right GPU available? (`nvidia-smi`)
4. Is there enough disk space? (`df -h`)
