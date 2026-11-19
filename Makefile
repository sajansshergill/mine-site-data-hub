COMPOSE = docker compose
s ?= api
shift ?= latest

.PHONY: up down logs seed test test-integration test-all lint dbt-run dbt-test report chaos deploy deploy-site streamlit fmt

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f $(s)

seed:
	$(COMPOSE) exec orchestration python /app/schemas/register_schemas.py
	$(COMPOSE) exec orchestration alembic -c /app/warehouse/alembic.ini upgrade head
	$(COMPOSE) exec orchestration dbt seed --project-dir /app/warehouse/dbt --profiles-dir /app/warehouse/dbt
	$(COMPOSE) exec orchestration python -m simulators.batch.generate_plan --out /app/data/drop/mine_plan.xlsx
	$(COMPOSE) exec orchestration python -m simulators.batch.generate_work_orders --out /app/data/drop/work_orders.csv
	$(COMPOSE) exec orchestration python -m simulators.batch.generate_assays --out /app/data/drop/assays.csv

dbt-run:
	$(COMPOSE) exec orchestration dbt run --project-dir /app/warehouse/dbt --profiles-dir /app/warehouse/dbt

dbt-test:
	$(COMPOSE) exec orchestration dbt test --project-dir /app/warehouse/dbt --profiles-dir /app/warehouse/dbt

report:
	$(COMPOSE) exec orchestration python -m reporting.shift_report --shift $(shift)

chaos:
	$(COMPOSE) restart sim-plant-opcua
	$(COMPOSE) exec sim-fleet python -c "print('fault rate raised via FAULT_RATE env on next restart')"
	FAULT_RATE=0.2 $(COMPOSE) up -d sim-fleet

test:
	pytest -m "not integration" -q
	busted fluent-bit/tests

test-integration:
	pytest -m integration -q

test-all: test test-integration

lint:
	ruff check .
	mypy libs api kpi_engine stream_processor connectors
	sqlfluff lint warehouse/dbt/models --dialect postgres

fmt:
	ruff format .

deploy:
	@if [ "$$(uname -s)" = "Darwin" ]; then \
		ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/site-local.yml; \
	else \
		ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/site.yml; \
	fi

deploy-site:
	ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/site.yml

streamlit:
	$(COMPOSE) up -d --build streamlit
	@echo "Streamlit: http://localhost:8501"