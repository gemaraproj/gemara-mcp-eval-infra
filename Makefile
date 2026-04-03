.PHONY: all corpus-validate eval eval-dfah eval-mcp-eval eval-deepeval report compare clean

-include .env
export

CORPUS_DIR := corpus
EVAL_DIR := eval
ANALYSIS_DIR := analysis
RESULTS_DIR := results
CONTAINER_RUNTIME ?= docker

all: corpus-validate eval report

# --- Corpus ---

# Validate corpus/inputs/tc-*-valid-*.yaml against the Gemara CUE schemas.
# Requires GEMARA_SCHEMA_PATH to point to a gemara schema checkout.
# Gracefully skips (warning only) when GEMARA_SCHEMA_PATH is unset.
corpus-validate:
	@echo "==> Validating corpus inputs against Gemara CUE schemas..."
	python3 scripts/corpus_validate.py
	@echo "==> Corpus validation complete."

# --- Individual Evaluations ---

eval-dfah: $(RESULTS_DIR)
	@echo "==> Running DFAH trajectory determinism harness..."
	cd $(EVAL_DIR)/dfah && python3 harness.py \
		--benchmarks benchmarks/ \
		--output ../../$(RESULTS_DIR)/dfah.json
	@echo "==> DFAH complete."

eval-mcp-eval: $(RESULTS_DIR)
	@echo "==> Running mcp-eval scenarios..."
	cd $(EVAL_DIR)/mcp-eval && python3 run_mcp_eval.py \
		--corpus ../../$(CORPUS_DIR) \
		--output ../../$(RESULTS_DIR)/mcp-eval.json
	@echo "==> mcp-eval complete."

eval-deepeval: $(RESULTS_DIR)
	@echo "==> Running DeepEval output determinism (no LLM)..."
	cd $(EVAL_DIR)/deepeval && python3 -m pytest \
		test_output_determinism.py \
		--tb=short -q \
		--timeout=120 \
		--json-report --json-report-file=../../$(RESULTS_DIR)/deepeval.json
	@echo "==> DeepEval complete."

eval: eval-dfah eval-mcp-eval eval-deepeval

# --- Analysis ---

report: $(RESULTS_DIR)
	@echo "==> Generating NFR6 output-determinism report..."
	python3 $(ANALYSIS_DIR)/nfr6_report.py \
		--results-dir $(RESULTS_DIR) \
		--threshold 0.9 \
		--output $(RESULTS_DIR)/nfr6-report.json
	@echo "==> NFR6 report: $(RESULTS_DIR)/nfr6-report.json"

compare:
	python3 $(ANALYSIS_DIR)/compare_results.py \
		--results-dir $(RESULTS_DIR)

# --- Helpers ---

$(RESULTS_DIR):
	mkdir -p $(RESULTS_DIR)

clean:
	rm -rf $(RESULTS_DIR)
	@echo "Results cleaned."
