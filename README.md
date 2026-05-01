# gemara-mcp-eval

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

NFR6 evaluation harness — **output determinism, no LLM required**.

This repo measures whether `gemara-mcp` produces identical structured artifacts across repeated runs (NFR6: ≥ 90% determinism). It is a standalone extraction of the Phase 1 POC work from the full `gemara-mcp-eval` suite.

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
pip install -r scripts/requirements.txt
pip install -r eval/dfah/requirements.txt
pip install -r eval/mcp-eval/requirements.txt
pip install -r eval/deepeval/requirements.txt
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `GEMARA_MCP_IMAGE` | `ghcr.io/gemaraproj/gemara-mcp:0.1.0` | Container image to evaluate |
| `GEMARA_MCP_MODE` | `artifact` | Server mode passed to the container |
| `CONTAINER_RUNTIME` | `docker` | `docker` or `podman` |
| `GEMARA_SCHEMA_PATH` | _(unset)_ | Path to a local `gemaraproj/gemara` checkout for `corpus-validate` |

All four are read from `.env` automatically by the Makefile (`-include .env`).

---

## Corpus validation (recommended before running harnesses)

`corpus-validate` checks that the test fixtures in `corpus/inputs/` still match
the current Gemara CUE schemas. Run this whenever the gemara schema or the
`gemara-mcp` image version changes. It catches schema drift early — before the
harnesses produce confusing failures.

Requires a local checkout of [gemaraproj/gemara](https://github.com/gemaraproj/gemara)
and the [`cue` CLI](https://cuelang.org/docs/install/):

```bash
# Clone the schema at the same ref used to build the image you're testing
git clone --depth 1 --branch v1.0.0-rc.2 https://github.com/gemaraproj/gemara /tmp/gemara

export GEMARA_SCHEMA_PATH=/tmp/gemara
make corpus-validate
```

If any fixture fails, the output tells you exactly which field no longer matches
the schema. Fix the fixture before running the harnesses.

In CI, `corpus-validate` runs automatically (see [CI](#ci) below).

---

## Running

```bash
# Run corpus-validate, all three harnesses, and generate the NFR6 report
make

# Or run individually
make eval-dfah
make eval-mcp-eval
make eval-deepeval

# Generate the report separately
make report
```

Results land in `results/`. The NFR6 report is at `results/nfr6-report.json`.

---

## Results

| File | Contents |
|---|---|
| `results/dfah.json` | DFAH trajectory determinism per benchmark and case |
| `results/mcp-eval.json` | Per-scenario results with `match_rate` per run |
| `results/deepeval.json` | pytest-json-report output |
| `results/nfr6-report.json` | Aggregated NFR6 verdict, overall score, and per-tool breakdown |

---

## Harnesses

| Harness | What it measures |
|---|---|
| `eval/dfah` | DFAH trajectory determinism — repeated tool-call sequences produce identical output |
| `eval/mcp-eval` | Scenario-based MCP response determinism against `corpus/` fixtures |
| `eval/deepeval` | DeepEval pytest assertions on output structure and field stability |

---

## Local service (optional)

`docker-compose.yml` defines a local `gemara-mcp` service for development convenience:

```bash
docker compose up
```

The harnesses do not require `docker compose` — each harness spawns the container directly via MCP stdio transport. The compose file is provided as an optional alternative for running the server independently.

---

## Integration contract

This repo takes the `gemara-mcp` Docker image as its only external input:

```
GEMARA_MCP_IMAGE=ghcr.io/your-org/gemara-mcp:<tag>
```

The upstream project builds and publishes the image; this repo evaluates it and returns a `PASS` or `FAIL` NFR6 verdict.

### Reusable workflow (`workflow_call`)

The `gemara-mcp` release pipeline calls this workflow directly as a post-release
step, pinning the image and schema ref to the same build:

```yaml
# In the gemara-mcp release workflow
jobs:
  nfr6-eval:
    needs: release
    uses: gemaraproj/gemara-mcp-eval-infra/.github/workflows/determinism-check.yml@main
    with:
      gemara_mcp_image: "ghcr.io/gemaraproj/gemara-mcp:${{ github.ref_name }}"
      gemara_schema_ref: "${{ github.ref_name }}"
```

### Manual dispatch (`workflow_dispatch`)

Pass both `gemara_mcp_image` and `gemara_schema_ref` to pin both the server and
the schema to the same version:

```
gemara_mcp_image:  ghcr.io/your-org/gemara-mcp:sha-abc123
gemara_schema_ref: v1.0.0-rc.2
```

---

## CI

`.github/workflows/determinism-check.yml` runs on:

| Trigger | When | Image | Schema ref |
|---|---|---|---|
| `push` / `pull_request` | Every push and PR to `main` | `:latest` | `main` |
| `workflow_call` | Called by `gemara-mcp` release pipeline | Pinned by caller | Pinned by caller |
| `workflow_dispatch` | Manual trigger via GitHub UI or API | User-specified | User-specified |
| `schedule` | Weekly (Monday 06:00 UTC) | `:latest` | `main` |

**Step order:**
1. Install Python deps
2. Clone `gemaraproj/gemara` at `gemara_schema_ref` (default: `main`)
3. Install `cue` CLI
4. **`corpus-validate`** — hard gate: if any valid fixture fails the schema, the job stops here with a clear schema-drift error before any harness runs
5. Pull the `gemara-mcp` image
6. Run the three harnesses (`dfah`, `mcp-eval`, `deepeval`) — each runs independently with `continue-on-error: true` so a partial failure still uploads available results
7. Generate and upload NFR6 report
8. Exit 1 if NFR6 score < 90%

---

## Make targets

| Target | Description |
|---|---|
| `make` / `make all` | Run corpus-validate, all harnesses, and generate report |
| `make corpus-validate` | Validate corpus fixtures against CUE schemas (requires `GEMARA_SCHEMA_PATH`) |
| `make eval` | Run all three harnesses |
| `make eval-dfah` | DFAH harness only |
| `make eval-mcp-eval` | mcp-eval harness only |
| `make eval-deepeval` | DeepEval harness only |
| `make report` | Generate NFR6 report from existing results |
| `make compare` | Compare result sets |
| `make clean` | Remove `results/` |
