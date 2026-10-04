.PHONY: install quality test test-public public-export synthetic design-power state-panel monthly-state-panel state-replay state-model-comparison state-redesign state-subspace state-instability state-instability-amendment run010-fetch vintage-robustness inventory-audit contract-audit clean

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

install:
	$(PYTHON) -m pip install -e '.[dev]'

quality:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m mypy src

test:
	$(PYTHON) -m coverage run -m unittest discover -s tests -v
	$(PYTHON) -m coverage report

test-public:
	$(PYTHON) -m coverage run --branch --source shockbridge_state_risk scripts/run_public_tests.py --expected-evidence-skips 7
	$(PYTHON) -m coverage report --fail-under=87

public-export:
	$(PYTHON) scripts/build_public_export.py --receipt reports/methodology/run_013_public_export_build.audit.json
	$(PYTHON) scripts/audit_public_export.py artifacts/public-export/shockbridge-state-reliability --output reports/methodology/run_013_public_export_security.audit.json
	$(PYTHON) scripts/verify_public_export.py artifacts/public-export/shockbridge-state-reliability --archive artifacts/public-export/shockbridge-state-reliability.tar.gz --bundle artifacts/public-export/shockbridge-state-reliability.bundle --output reports/methodology/run_013_public_export_verification.audit.json

synthetic:
	$(PYTHON) -m shockbridge_state_risk synthetic-replay

design-power:
	$(PYTHON) -m shockbridge_state_risk design-power experiments/design_power_v1.yaml --output reports/methodology/state_support_power_v1.json

state-panel:
	$(PYTHON) -m shockbridge_state_risk build-state-panel research/state_sources_v1.yaml data/processed/state_panel_v1.csv --audit-output reports/methodology/state_panel_v1.audit.json

monthly-state-panel:
	$(PYTHON) -m shockbridge_state_risk build-monthly-state-panel experiments/monthly_state_panel_v2.yaml data/processed/monthly_state_panel_v2.csv --audit-output reports/methodology/monthly_state_panel_v2.audit.json

state-replay:
	$(PYTHON) -m shockbridge_state_risk state-replay experiments/state_replay_v1.yaml data/processed/state_probabilities_v1.csv --audit-output reports/methodology/state_replay_v1.audit.json

state-model-comparison:
	$(PYTHON) -m shockbridge_state_risk compare-state-models experiments/state_model_comparison_v1.yaml data/processed/state_model_comparison_v1.csv --audit-output reports/methodology/state_model_comparison_v1.audit.json

state-redesign:
	$(PYTHON) -m shockbridge_state_risk run-state-redesign experiments/state_model_run007_v1.yaml --factor-output data/processed/state_factor_run007_v1.csv --challenger-output data/processed/state_challengers_run007_v1.csv --restart-output data/processed/state_restart_provenance_run007_v1.jsonl --audit-output reports/methodology/state_model_run007_v1.audit.json

state-subspace:
	$(PYTHON) -m shockbridge_state_risk run-state-subspace experiments/state_model_run008_v1.yaml --subspace-output data/processed/state_subspace_run008_v1.csv --fixed-factor-output data/processed/state_fixed_factor_run008_v1.csv --two-factor-output data/processed/state_two_factor_run008_v1.csv --audit-output reports/methodology/state_model_run008_v1.audit.json

state-instability:
	$(PYTHON) -m shockbridge_state_risk run-state-instability experiments/state_instability_run009_v1.yaml --diagnostic-output data/processed/state_instability_run009_v1.csv --episode-output data/processed/state_instability_episodes_run009_v1.csv --audit-output reports/methodology/state_instability_run009_v1.audit.json

state-instability-amendment:
	$(PYTHON) -m shockbridge_state_risk amend-state-instability-episodes experiments/state_instability_run009_v1_amendment_1.yaml --episode-output data/processed/state_instability_episodes_run009_v1_amendment_1.csv --audit-output reports/methodology/state_instability_run009_v1_amendment_1.audit.json

run010-fetch:
	$(PYTHON) -m shockbridge_state_risk fetch-run010-sources research/methodology/run_010_vintage_robustness_proposal_v1.yaml data/raw/ecb_state --manifest-output data/manifests/run010_latest_sources_v1.yaml

vintage-robustness:
	$(PYTHON) -m shockbridge_state_risk run-vintage-robustness experiments/state_vintage_robustness_run010_v1.yaml --comparison-output data/processed/state_vintage_comparison_run010_v1.csv --geometry-output data/processed/state_vintage_geometry_run010_v1.csv --episode-output data/processed/state_vintage_episodes_run010_v1.csv --audit-output reports/methodology/state_vintage_robustness_run010_v1.audit.json

inventory-audit:
	$(PYTHON) -m shockbridge_state_risk verify-artifacts data/manifests/local_artifact_inventory_2026-10-02.yaml

contract-audit:
	$(PYTHON) -m shockbridge_state_risk audit-contract research/empirical_contract_v1.yaml

clean:
	$(PYTHON) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('.pytest_cache', '.mypy_cache', '.ruff_cache', 'htmlcov', 'build', 'dist')]"
