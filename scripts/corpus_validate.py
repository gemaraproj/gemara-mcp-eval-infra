#!/usr/bin/env python3
"""
Validate corpus/inputs/tc-*-valid-*.yaml fixtures against Gemara CUE schemas.

Each fixture's metadata.type field determines which CUE definition to validate
against (e.g. type: GuidanceCatalog → validates against #GuidanceCatalog).

Only 'valid' fixtures (tc-*-valid-*.yaml) are validated — invalid fixtures are
intentionally malformed and are expected to fail schema validation.

Requires:
  - GEMARA_SCHEMA_PATH env var pointing to a checked-out gemara schema directory
  - the `cue` CLI on PATH

Exit codes:
  0  all valid fixtures pass schema validation
  1  one or more fixtures fail (schema drift detected)
  2  GEMARA_SCHEMA_PATH not set (skips with a warning, exits 0 if --warn-only)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus" / "inputs"


def cue_validate(schema_dir: Path, definition: str, fixture: Path) -> tuple[bool, str]:
    """Run `cue vet -d #Definition . fixture` from the schema directory."""
    result = subprocess.run(
        ["cue", "vet", "-d", definition, ".", str(fixture.resolve())],
        capture_output=True,
        text=True,
        cwd=str(schema_dir),
    )
    if result.returncode == 0:
        return True, ""
    err = (result.stderr.strip() or result.stdout.strip()).splitlines()[0]
    return False, err


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate corpus inputs against Gemara CUE schemas")
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Exit 0 even if GEMARA_SCHEMA_PATH is not set (print warning only)",
    )
    parser.add_argument(
        "--schema-path",
        default=os.environ.get("GEMARA_SCHEMA_PATH"),
        help="Path to gemara schema directory (overrides GEMARA_SCHEMA_PATH env var)",
    )
    args = parser.parse_args()

    schema_path = args.schema_path
    if not schema_path:
        print("WARN: GEMARA_SCHEMA_PATH is not set — corpus validation skipped.")
        print("      Set GEMARA_SCHEMA_PATH=/path/to/gemara (or clone gemaraproj/gemara) to enable.")
        print("      Example: GEMARA_SCHEMA_PATH=/tmp/gemara make corpus-validate")
        return 0

    schema_dir = Path(schema_path)
    if not schema_dir.is_dir():
        print(f"ERROR: GEMARA_SCHEMA_PATH={schema_path!r} is not a directory.")
        return 1

    # Verify cue is available
    if subprocess.run(["cue", "version"], capture_output=True).returncode != 0:
        print("ERROR: `cue` CLI not found on PATH. Install from https://cuelang.org/docs/install/")
        return 1

    fixtures = sorted(CORPUS_DIR.glob("tc-*-valid-*.yaml"))
    if not fixtures:
        print(f"No tc-*-valid-*.yaml fixtures found in {CORPUS_DIR}")
        return 0

    print(f"==> Validating {len(fixtures)} corpus fixtures against schemas at {schema_dir}")
    print()

    passed, failed = 0, 0
    failures: list[tuple[str, str, str]] = []

    for fixture in fixtures:
        try:
            with open(fixture) as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"  SKIP  {fixture.name}  (parse error: {e})")
            continue

        artifact_type = (data or {}).get("metadata", {}).get("type", "")
        if not artifact_type:
            print(f"  SKIP  {fixture.name}  (no metadata.type)")
            continue

        definition = f"#{artifact_type}"
        ok, err = cue_validate(schema_dir, definition, fixture)

        if ok:
            print(f"  PASS  {fixture.name}  ({artifact_type})")
            passed += 1
        else:
            print(f"  FAIL  {fixture.name}  ({artifact_type})")
            print(f"        {err}")
            failures.append((fixture.name, artifact_type, err))
            failed += 1

    print()
    print(f"Result: {passed} passed, {failed} failed ({passed + failed} fixtures checked)")

    if failures:
        print()
        print("Schema drift detected — the following fixtures no longer match the current schema:")
        for name, typ, err in failures:
            print(f"  {name} ({typ}): {err}")
        print()
        print("Fix: update corpus/inputs/ fixtures to match the current schema at GEMARA_SCHEMA_PATH,")
        print("     then update corpus/golden/ expected outputs if the server response also changed.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
