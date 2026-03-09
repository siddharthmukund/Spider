.PHONY: build up down test-ci run-local

build:
	docker build -t seocrawler:local .

up:
	docker-compose up --build

down:
	docker-compose down

run-local:
	# run app locally
	uvicorn webapp.main:app --reload --host 127.0.0.1 --port 8000

test-ci:
	# Run tests in CI-like environment with Redis & Celery
	env RUN_CELERY_INTEGRATION=1 REDIS_URL=redis://localhost:6379/0 USE_CELERY=1 \ 
	    celery -A webapp.tasks worker --loglevel=info &
	pytest -q
