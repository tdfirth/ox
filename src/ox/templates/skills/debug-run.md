# Debug Run

Guide for debugging failed experiments.

## First Steps

```bash
# Check experiment status
ox show <experiment-id>

# Look at the command that was run
ox show <experiment-id> | grep Command
```

If the experiment status is "failed", the error traceback was printed when it ran. Check your terminal history or logs.

## Common Failures

### Config Errors

**Symptom:** `ValidationError` from Pydantic before training starts.

```bash
# Check what the script expects
ox config-schema src/my_research/scripts/train.py

# Compare with your config
cat studies/<study>/experiments/<exp>/config.yaml
```

Common issues:
- Typo in field name
- Wrong type (string where int is expected)
- Missing required field (no default in Config class)

### Import Errors

**Symptom:** `ModuleNotFoundError` or `ImportError`.

```bash
# Check your environment
uv sync

# Verify the package is installed
uv pip list | grep <package>
```

### Out of Memory (OOM)

**Symptom:** `RuntimeError: CUDA out of memory` or process killed by OS.

Fixes:
- Reduce `batch_size`
- Reduce `hidden_dim` or `num_layers`
- Use gradient accumulation
- Use mixed precision (torch.cuda.amp)
- Use a smaller model for debugging

```bash
# Check GPU memory
nvidia-smi

# Monitor during training
watch -n 1 nvidia-smi
```

### NaN Loss

**Symptom:** Loss becomes `nan` during training, model produces garbage.

Common causes:
- Learning rate too high — try 10x lower
- Missing gradient clipping — add `torch.nn.utils.clip_grad_norm_`
- Data issues — NaN or Inf values in inputs
- Numerical instability — check for division by zero, log(0)

### Hanging / No Progress

**Symptom:** Training seems to start but nothing happens.

Check:
- Is the data loader blocking? (try with a small dataset first)
- Is there a distributed training deadlock? (check if all ranks are active)
- Is the process actually running? (`ps aux | grep python`)

## Re-running After a Fix

After fixing the issue:

```bash
# Commit the fix
git add -A
git commit -m "Fix: reduce lr to prevent NaN loss"

# Re-run the same experiment
ox run src/my_research/scripts/train.py \
  --config studies/<study>/experiments/<exp>/config.yaml \
  --experiment <exp-id>
```

The experiment status will transition: failed -> running -> (hopefully) completed.

## Debugging Strategies

1. **Reproduce with minimal config.** Use small values for epochs, batch_size, hidden_dim. Get a fast iteration loop.

2. **Add checkpoints.** Print or log intermediate values to narrow down where things go wrong.

3. **Test components independently.** If the model forward pass works, test the loss. If the loss works, test the backward pass.

4. **Compare with a known-good run.** Diff the configs and code between a working experiment and the failing one.

5. **Check the data.** Many training failures come from data issues.

```python
# Quick data sanity check
import torch
for batch in dataloader:
    assert not torch.isnan(batch).any(), "NaN in input data"
    assert not torch.isinf(batch).any(), "Inf in input data"
    break
```

## GPU / CUDA Debugging

```bash
# Check CUDA is available
python -c "import torch; print(torch.cuda.is_available())"

# Check GPU details
python -c "import torch; print(torch.cuda.get_device_name(0))"

# Check CUDA version
nvcc --version
python -c "import torch; print(torch.version.cuda)"
```
