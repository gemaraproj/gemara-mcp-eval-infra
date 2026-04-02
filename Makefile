.PHONY: all eval-phase1 eval-all eval-dfah eval-mcp-eval eval-deepeval-phase1 report report-phase1 compare clean

-include .env
export

CORPUS_DIR := corpus
EVAL_DIR := eval
ANALYSIS_DIR := analysis
RESULTS_DIR := results
CONTAINER_RUNTIME ?= docker

all: eval-phase1 report-phase1

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

eval-deepeval-phase1: $(RESULTS_DIR)
	@echo "==> Running DeepEval Phase 1 output determinism (no LLM)..."
	cd $(EVAL_DIR)/deepeval && python3 -m pytest \
		test_output_determinism.py \
		--tb=short -q \
		--json-report --json-report-file=../../$(RESULTS_DIR)/deepeval-phase1.json
	@echo "==> DeepEval Phase 1 complete."

eval-all: eval-phase1

eval-phase1: eval-dfah eval-mcp-eval eval-deepeval-phase1

# --- Analysis ---

report-phase1: $(RESULTS_DIR)
	@echo "==> Generating Phase 1 NFR6 report (output determinism, no LLM)..."
	python3 $(ANALYSIS_DIR)/nfr6_report.py \
		--phase 1 \
		--results-dir $(RESULTS_DIR) \
		--threshold 0.9 \
		--output $(RESULTS_DIR)/nfr6-phase1-report.json
	@echo "==> Phase 1 NFR6 report: $(RESULTS_DIR)/nfr6-phase1-report.json"

report: report-phase1

compare:
	python3 $(ANALYSIS_DIR)/compare_results.py \
		--results-dir $(RESULTS_DIR)

# --- Helpers ---

$(RESULTS_DIR):
	mkdir -p $(RESULTS_DIR)

clean:
	rm -rf $(RESULTS_DIR)
	@echo "Results cleaned."
