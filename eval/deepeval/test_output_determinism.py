"""
Output determinism test for validate_gemara_artifact.

Calls the live gemara-mcp server N times per scenario and asserts that every
response is byte-for-byte identical.  No LLM, no Ollama, no GEval — Docker
for the MCP container is the only external dependency.

Runs as part of the NFR6 CI gate via `make eval-deepeval`.
Results are written via pytest-json-report to results/deepeval.json.
"""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "corpus"


def _det_config(scenario: dict) -> dict:
    """Return the determinism config, falling back to the flat block."""
    det = scenario["determinism"]
    return det.get("phase1", det)


def test_validation_determinism(mcp_client, tool_scenarios, event_loop):
    """validate_gemara_artifact must produce byte-identical output on every run."""
    loop = event_loop

    scenarios = tool_scenarios
    if not scenarios:
        with open(CORPUS_DIR / "scenarios.yaml") as f:
            all_scenarios = yaml.safe_load(f)["scenarios"]
        scenarios = [s for s in all_scenarios if s["type"] == "tool"]

    for scenario in scenarios:
        input_path = CORPUS_DIR / scenario["input_file"]
        if not input_path.exists():
            pytest.skip(f"Input file missing: {input_path}")

        artifact_content = input_path.read_text()
        definition = scenario["tool_params"]["definition"]
        det = _det_config(scenario)
        num_runs = det.get("runs", 20)
        threshold = det.get("threshold", 1.0)

        async def call_once():
            result = await mcp_client.call_tool("validate_gemara_artifact", {
                "artifact_content": artifact_content,
                "definition": definition,
            })
            return result.text

        outputs = [loop.run_until_complete(call_once()) for _ in range(num_runs)]

        unique_outputs = set(outputs)
        # determinism_rate: 1.0 when all outputs are identical, lower when they diverge
        determinism_rate = 1.0 / len(unique_outputs) if unique_outputs else 0.0

        assert determinism_rate >= threshold, (
            f"Scenario {scenario['id']}: determinism_rate={determinism_rate:.4f} "
            f"below threshold={threshold} "
            f"({len(unique_outputs)} unique outputs across {num_runs} runs)"
        )
