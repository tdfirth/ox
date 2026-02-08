# Plan Study

Guide for planning and scoping a research study in an ox project.

## What is a Study?

A study is a research theme or line of inquiry — "sparse attention mechanisms", "scaling laws for small models", etc. It lives in `studies/<name>/` and contains multiple experiments.

## Creating a Study

```bash
ox new study "descriptive name"
```

This creates `studies/<slug>/README.md` and an `experiments/` directory.

## Writing a Good README

The study README is the most important document. It should be a living record of what you're investigating and what you've found.

### Structure

```markdown
# Study Name

## Goals
What are you trying to learn? Be specific. "Understand the effect of sparse attention on perplexity for models under 100M params" is better than "try sparse attention".

## Hypotheses
What do you expect to find? Writing this down before running experiments prevents post-hoc rationalization.

1. Sparse attention will reduce memory usage by ~40% with <5% perplexity degradation
2. The benefit scales with sequence length

## Background
- Prior work, papers, relevant results
- Links to related studies in this project
- Key numbers to beat (baselines)

## Experiment Plan
- baseline: Standard dense attention (control)
- sparse-v1: Top-k sparse attention, k=32
- sparse-v2: Local window attention, window=128
- sparse-v3: Combined top-k + local window

## Key Findings
Updated as experiments complete. Include links to experiment NOTES.md files.
```

## Scoping Tips

- **Start with a baseline.** Always. You need something to compare against.
- **One variable at a time.** Each experiment should test one specific hypothesis.
- **Plan ablations upfront.** What should you hold constant? What should vary?
- **Define success criteria.** How will you know if the study answered your question?
- **Time-box.** Set a rough limit on how many experiments before reassessing.

## Breaking Down a Research Question

1. What is the core question?
2. What is the simplest experiment that could provide evidence?
3. What baseline do I need?
4. What ablations would help isolate the effect?
5. What metrics will I use to decide?

## When to Create a New Study vs. Extend an Existing One

Create a new study when:
- The research question is fundamentally different
- You'd want to write a separate section in a paper

Extend an existing study when:
- You're following up on a finding from that study
- The experiments share the same baselines
- The question is a refinement of the original

## Example Well-Structured Study

```
studies/sparse-attention/
├── README.md
└── experiments/
    ├── dense-baseline/       # Control: standard transformer
    ├── topk-k16/             # Sparse: top-k with k=16
    ├── topk-k32/             # Sparse: top-k with k=32
    ├── topk-k64/             # Sparse: top-k with k=64
    ├── local-w64/            # Sparse: local window, w=64
    ├── local-w128/           # Sparse: local window, w=128
    └── combined-k32-w64/     # Sparse: top-k + local window
```

Each experiment folder has clear naming that indicates what varies.
