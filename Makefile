.PHONY: help test test-article test-player init-db docker-up docker-down streamlit clean db-shell db-tables db-articles db-players

help:
	@echo "Player Risk Service - Available Commands"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      - Start Docker services"
	@echo "  make docker-down    - Stop Docker services"
	@echo ""
	@echo "Database:"
	@echo "  make init-db        - Initialize database tables"
	@echo "  make db-shell       - Open PostgreSQL shell"
	@echo "  make db-tables      - List all tables"
	@echo "  make db-articles    - View all articles"
	@echo "  make db-players     - View all players"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-article   - Test Article model"
	@echo "  make test-player    - Test Player model"
	@echo ""
	@echo "Development:"
	@echo "  make streamlit      - Start Streamlit dashboard"
	@echo "  make clean          - Remove Python cache files"

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

init-db:
	python -m scripts.init_db

test:
	python run_tests.py

test-article:
	python -m scripts.test_article

test-player:
	python -m scripts.test_player

streamlit:
	streamlit run streamlit_app/app.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Database inspection commands
# These commands read POSTGRES_USER and POSTGRES_DB from your .env file
include .env
export

db-shell:
	docker-compose exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

db-tables:
	@echo "Tables in database:"
	@docker-compose exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "\dt"

db-articles:
	@echo "Articles in database:"
	@docker-compose exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "SELECT id, title, source, published_at FROM articles ORDER BY published_at DESC LIMIT 10;"

db-players:
	@echo "Players in database:"
	@docker-compose exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "SELECT id, name, team, risk_tag, fixture FROM players ORDER BY created_at DESC;"

