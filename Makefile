.PHONY: setup dev down reset logs seed

setup:
	docker compose up -d postgres redis
	@echo "Waiting for services to be healthy..."
	@sleep 5
	docker compose --profile seed run --rm seeder
	docker compose up -d api frontend
	@echo "LogisticsMind AI is running at http://localhost:3000"

dev:
	docker compose up postgres redis api

down:
	docker compose down

reset:
	docker compose down -v
	$(MAKE) setup

logs:
	docker compose logs -f api

seed:
	docker compose --profile seed run --rm seeder
