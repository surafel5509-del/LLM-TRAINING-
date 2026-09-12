.PHONY: install dev migrate test train-test docker
install:
	python -m pip install -r backend/requirements.txt
	cd frontend && npm install

dev:
	uvicorn app.main:app --app-dir backend --reload

migrate:
	alembic -c backend/alembic.ini upgrade head

test:
	PYTHONPATH=backend pytest -q backend/tests

train-test:
	PYTHONPATH=backend python -m app.demo_dataset

docker:
	docker compose up --build
