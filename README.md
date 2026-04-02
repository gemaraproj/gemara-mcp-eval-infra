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
# Run all three harnesses and generate the NFR6 report
make

# Or run individually
make eval-dfah
make eval-mcp-eval
make eval-deepeval

# Generate the report separately
make report
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

`.github/workflows/determinism-check.yml` runs on every push and PR to `main`.

**Step order:**
1. Install Python deps
2. Install `cue` CLI
3. Clone `gemaraproj/gemara` at `gemara_schema_ref` (default: `main`)
4. **`corpus-validate`** — hard gate: if any valid fixture fails the schema, the job stops here with a clear schema-drift error before any harness runs
5. Pull the `gemara-mcp` image
6. Run the three harnesses (`dfah`, `mcp-eval`, `deepeval`)
7. Generate and upload NFR6 report
8. Exit 1 if NFR6 score < 90%

When triggering via `workflow_dispatch`, pass both `gemara_mcp_image` and
`gemara_schema_ref` to pin both the server and the schema to the same version:

```
gemara_mcp_image:  ghcr.io/your-org/gemara-mcp:sha-abc123
gemara_schema_ref: v1.0.0-rc.2
```

---

## Make targets

| Target | Description |
|---|---|
| `make` / `make all` | Run all harnesses + generate report |
| `make corpus-validate` | Validate corpus fixtures against CUE schemas (requires `GEMARA_SCHEMA_PATH`) |
| `make eval` | Run all three harnesses |
| `make eval-dfah` | DFAH harness only |
| `make eval-mcp-eval` | mcp-eval harness only |
| `make eval-deepeval` | DeepEval harness only |
| `make report` | Generate NFR6 report from existing results |
| `make compare` | Compare result sets |
| `make clean` | Remove `results/` |
