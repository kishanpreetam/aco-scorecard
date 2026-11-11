# ACO Scorecard: one command runs the whole pipeline (make all).
PY  := .venv/bin/python
DBT := .venv/bin/dbt
UV  ?= uv

export ACO_WAREHOUSE := $(CURDIR)/data/warehouse/aco.duckdb
export ACO_DUCKDB_MEMORY_LIMIT := 1GB
export DBT_PROFILES_DIR := $(CURDIR)/warehouse
export DBT_SEND_ANONYMOUS_USAGE_STATS := false
export DO_NOT_TRACK := 1

.PHONY: all setup download discover ingest staging dbt semantic dashboard docs monitor test clean

all: download discover ingest staging dbt semantic dashboard docs monitor test

setup:
	$(UV) venv --python 3.12 .venv
	$(UV) pip install --python $(PY) -r requirements-lock.txt

download:            ## fetch pinned CMS files (reuses verified local copies)
	$(PY) -m aco_scorecard.download

discover:            ## re-read the data.cms.gov catalog for new or revised files (a failure here does not stop the run)
	-$(PY) -m aco_scorecard.download --discover

ingest:              ## load raw CSVs into DuckDB as text, with schema checks
	$(PY) -m aco_scorecard.ingest

staging:             ## regenerate dbt staging models from config/schema_mapping.yml
	$(PY) -m aco_scorecard.gen_staging

dbt:                 ## build and test every dbt model, seed, data test and unit test
	$(DBT) build --project-dir warehouse
	cp warehouse/target/run_results.json data/warehouse/dbt_run_results.json

semantic:            ## answer business questions through MetricFlow and check them against plain SQL
	$(PY) -m aco_scorecard.semantic_tests

dashboard:           ## results/dashboard.html and results/metrics.json
	$(PY) -m aco_scorecard.dashboard

docs:                ## docs/schema_mapping.md and docs/data_dictionary.md
	$(DBT) docs generate --project-dir warehouse --no-compile --quiet
	$(PY) -m aco_scorecard.docs

monitor:             ## results/pipeline_monitoring.json and .md
	$(PY) -m aco_scorecard.monitor

test:                ## pytest suite
	$(PY) -m pytest -q

clean:
	rm -rf warehouse/target warehouse/logs data/warehouse
