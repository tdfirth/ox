# Analyze Results

Guide for analyzing experiment results and drawing conclusions.

## Querying Results

```bash
# All completed experiments in a study
ox ls --study sparse-attention --status completed

# Complex queries
ox query "study = 'sparse-attention' AND status = 'completed' ORDER BY lr"

# Show full details
ox show my-experiment
```

## Reading Metrics (Local Tracker)

The local tracker writes JSONL files to `.ox/metrics/`. Each line is a JSON object:

```bash
# View all metrics for a run
cat .ox/metrics/<run-id>_metrics.jsonl

# Extract just loss values
cat .ox/metrics/<run-id>_metrics.jsonl | python -c "
import json, sys
for line in sys.stdin:
    d = json.loads(line)
    if d.get('type') == 'metrics' and 'loss' in d:
        print(f\"step={d.get('step', '?')}: loss={d['loss']:.4f}\")
"
```

## Comparing Runs

When comparing experiments, consider:

1. **Same baseline?** Are you comparing against the same control?
2. **Same evaluation?** Did all runs use the same eval set and metrics?
3. **Statistical significance?** One run is an anecdote. Multiple runs with different seeds give confidence.
4. **Resource cost?** A 1% improvement that takes 10x compute may not be worth it.

## Writing Good NOTES.md

After each experiment, update its NOTES.md:

```markdown
## Observations

- Training was stable, no NaN issues
- Loss plateaued around epoch 15
- Learning rate 1e-3 seems too high for this architecture

## Results

| Metric     | Value |
|------------|-------|
| Final loss | 2.34  |
| Best loss  | 2.31 (epoch 12) |
| Wall time  | 45 min |
| GPU memory | 8.2 GB peak |

## Conclusions

This learning rate is too aggressive. Try 3e-4 next.
See experiment lr-3e4 for follow-up.
```

Key elements:
- **Quantitative results** in a table
- **Qualitative observations** about training dynamics
- **Actionable conclusions** that inform next experiments
- **Links to follow-up** experiments

## Updating the Study README

After analyzing several experiments, update the study README's Key Findings:

```markdown
## Key Findings

1. Learning rate 3e-4 is optimal for this architecture (see experiments/lr-3e4)
2. Batch size has minimal effect above 32 (see experiments/bs-*)
3. Sparse attention reduces memory by 35% with only 2% perplexity increase
```

## Deciding What to Try Next

After analyzing results:

1. **Did the experiment answer the question?** If yes, what's the next question?
2. **Were results surprising?** Investigate unexpected findings.
3. **Is there a clear winner?** If not, what additional experiment would distinguish?
4. **Diminishing returns?** Know when to stop and move to a different study.

## Creating Visualizations

When helpful, create plots in the experiment directory or study directory.
Use matplotlib, plotly, or whatever tool is appropriate. Save as PNG or HTML.

The framework doesn't prescribe visualization tools — use what works for your data.
