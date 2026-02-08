# Query Experiments

Guide for finding and filtering experiments.

## Basic Listing

```bash
# All experiments
ox ls

# Filter by study
ox ls --study sparse-attention

# Filter by status
ox ls --status completed

# Filter by tag
ox ls --tag baseline

# Combine filters
ox ls --study sparse-attention --status completed --tag baseline
```

## SQL Queries with `ox query`

`ox query` uses DuckDB to run SQL WHERE clauses against your experiments. Config fields are flattened to top-level columns.

```bash
# Simple filters
ox query "status = 'completed'"
ox query "study = 'sparse-attention'"

# Numeric comparisons (these are config fields)
ox query "lr < 0.001"
ox query "epochs > 10 AND batch_size = 64"

# Sorting
ox query "status = 'completed' ORDER BY lr"
ox query "study = 'sparse-attention' ORDER BY updated_at DESC"

# Combining metadata and config
ox query "status = 'completed' AND lr < 0.001 AND hidden_dim >= 256"
```

## Available Columns

Metadata columns (always present):
- `id` — experiment slug
- `study` — study slug
- `status` — created, running, completed, failed, cancelled
- `created_at` — ISO timestamp
- `updated_at` — ISO timestamp
- `git_sha` — commit hash
- `command` — the ox run command used
- `tags` — list of tags
- `tracker_run_id` — tracker backend run ID

Config columns (vary by experiment):
- Whatever fields are in config.yaml become top-level columns
- e.g., `lr`, `batch_size`, `epochs`, `hidden_dim`

## Showing Experiment Details

```bash
# Full details including config and notes
ox show my-experiment-id

# The experiment ID is just the slug (e.g., "cosine-baseline")
# ox finds it across all studies
```

## Common Patterns

```bash
# Find the best performing run
ox query "status = 'completed' ORDER BY lr"

# Find all experiments for a specific architecture
ox query "num_layers = 6 AND hidden_dim = 512"

# Find failed runs to investigate
ox query "status = 'failed'"

# Find recent experiments
ox query "status = 'completed' ORDER BY updated_at DESC"
```

## Combining with Shell Tools

```bash
# Count experiments by status
ox ls | tail -n +3 | awk '{print $3}' | sort | uniq -c

# Get just experiment IDs
ox ls --study my-study | tail -n +3 | awk '{print $1}'
```

## Checking Status

```bash
# All running experiments
ox status

# Specific experiment
ox status my-experiment-id
```
