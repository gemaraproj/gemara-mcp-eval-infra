# gemara-mcp-eval-phase1

NFR6 Phase 1 evaluation harness — **output determinism, no LLM required**.

This repo measures whether `gemara-mcp` produces identical structured artifacts across repeated runs (NFR6: ≥ 90% determinism). It is a standalone extraction of the Phase 1 POC work from the full `gemara-mcp-eval` suite.

Phase 2 (LLM integration quality) is not included here. See `PHASE1-OUTPUT-DETERMINISM.md` for full technical details.

---

## Prerequisites

- Python 3.12+
- Docker or Podman
- The `gemara-mcp` image available locally or in a registry (see below)

No Ollama, no Node.js, no LLM API keys required.

---

## Setup

```bash
cp .env.example .env
# Edit .env and set GEMARA_MCP_IMAGE to the image you want to evaluate
```

Install Python dependencies:

```bash
pip install -r eval/dfah/requirements.txt
pip install -r eval/mcp-eval/requirements.txt
pip install -r eval/deepeval/requirements.txt
```

---

## Running

```bash
# Run all three Phase 1 harnesses and generate the NFR6 report
make

# Or run individually
make eval-dfah
make eval-mcp-eval
make eval-deepeval-phase1

# Generate the report separately
make report-phase1
```

Results land in `results/`. The NFR6 report is at `results/nfr6-phase1-report.json`.

---

## Harnesses

| Harness | What it measures |
|---|---|
| `eval/dfah` | DFAH trajectory determinism — repeated tool-call sequences produce identical output |
| `eval/mcp-eval` | Scenario-based MCP response determinism against `corpus/` fixtures |
| `eval/deepeval` | DeepEval pytest assertions on output structure and field stability |

---

## Integration contract

This repo takes the `gemara-mcp` Docker image as its only external input:

```
GEMARA_MCP_IMAGE=ghcr.io/your-org/gemara-mcp:<tag>
```

The upstream project builds and publishes the image; this repo evaluates it and returns a `PASS` or `FAIL` NFR6 verdict.

In CI, pass the image tag via the `workflow_dispatch` input `gemara_mcp_image`, or set it as a repository variable/secret that the workflow falls back to.

---

## CI

`.github/workflows/determinism-check.yml` runs on every push and PR to `main`. It exits 1 if the NFR6 score falls below the 90% threshold, blocking the merge.

---

## Make targets

| Target | Description |
|---|---|
| `make` / `make all` | Run phase 1 eval + generate report |
| `make eval-phase1` | Run all three harnesses |
| `make eval-dfah` | DFAH harness only |
| `make eval-mcp-eval` | mcp-eval harness only |
| `make eval-deepeval-phase1` | DeepEval Phase 1 only |
| `make report-phase1` | Generate NFR6 report from existing results |
| `make compare` | Compare result sets |
| `make clean` | Remove `results/` |
