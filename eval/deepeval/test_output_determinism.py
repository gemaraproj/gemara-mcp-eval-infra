"""
Output determinism test for validate_gemara_artifact.

Calls the live gemara-mcp server N times per scenario and asserts that every
response is byte-for-byte identical.  No LLM, no Ollama, no GEval — Docker
for the MCP container is the only external dependency.

Runs as part of the NFR6 CI gate via `make eval-deepeval`.
Results are written via pytest-json-report to results/deepeval.json.
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared.mcp_client import GemaraMCPClient

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "corpus"


def _det_config(scenario: dict) -> dict:
    """Return the determinism config, falling back to the flat block."""
    det = scenario["determinism"]
    return det.get("phase1", det)


def test_validation_determinism(tool_scenarios):
    """validate_gemara_artifact must produce byte-identical output on every run.

    The MCP client is created and torn down within a single asyncio.run() call
    so that anyio's cancel scopes are entered and exited in the same task.
    """

    async def run_all():
        async with GemaraMCPClient() as client:
            for scenario in tool_scenarios:
                input_path = CORPUS_DIR / scenario["input_file"]
                if not input_path.exists():
                    pytest.skip(f"Input file missing: {input_path}")

                artifact_content = input_path.read_text()
                definition = scenario["tool_params"]["definition"]
                det = _det_config(scenario)
                num_runs = det.get("runs", 20)
                threshold = det.get("threshold", 1.0)

                outputs = []
                for _ in range(num_runs):
                    result = await client.call_tool(
                        "validate_gemara_artifact",
                        {
                            "artifact_content": artifact_content,
                            "definition": definition,
                        },
                    )
                    outputs.append(result.text)

                unique_outputs = set(outputs)
                # 1.0 when all outputs are identical, lower when they diverge
                determinism_rate = 1.0 / len(unique_outputs) if unique_outputs else 0.0

                assert determinism_rate >= threshold, (
                    f"Scenario {scenario['id']}: determinism_rate={determinism_rate:.4f} "
                    f"below threshold={threshold} "
                    f"({len(unique_outputs)} unique outputs across {num_runs} runs)"
                )

    asyncio.run(run_all())
