.PHONY: help setup test test-article test-player test-grok test-research init-db db-reset docker-up docker-down streamlit clean db-shell db-tables db-articles db-players pipeline test-roster-sync test-transfermarkt test-roster-update

help:
	@echo "Player Risk Service - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Install dependencies + Playwright browser"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      - Start Docker services"
	@echo "  make docker-down    - Stop Docker services"
	@echo ""
	@echo "Database:"
	@echo "  make init-db        - Initialize database tables"
	@echo "  make db-reset       - Reset database (drops all tables!)"
	@echo "  make db-shell       - Open PostgreSQL shell"
	@echo "  make db-tables      - List all tables"
	@echo "  make db-articles    - View all articles"
	@echo "  make db-players     - View all players"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-article   - Test Article model"
	@echo "  make test-player    - Test Player model"
	@echo "  make test-grok      - Test Grok API client"
	@echo "  make test-research  - Test Research Agent"
	@echo "  make test-analyst   - Test Analyst Agent"
	@echo "  make test-shark     - Test Shark Agent"
	@echo "  make test-alert-save - Test Alert database save"
	@echo "  make test-roster-sync - Test Roster sync service"
	@echo ""
	@echo "Pipeline:"
	@echo "  make pipeline       - Run full agent pipeline"
	@echo ""
	@echo "Development:"
	@echo "  make streamlit      - Start Streamlit dashboard"
	@echo "  make clean          - Remove Python cache files"

setup:
	pip install -r requirements.txt
	playwright install chromium

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

init-db:
	python -m scripts.init_db

db-reset:
	@echo "yes" | python -m scripts.init_db --reset

test:
	python run_tests.py

test-article:
	python -m scripts.test_article

test-player:
	python -m scripts.test_player

test-grok:
	python -m scripts.test_grok_client

test-research-agent:
	python -m scripts.test_research_agent

test-analyst-agent:
	python -m scripts.test_analyst_agent

test-shark-agent:
	python -m scripts.test_shark_agent

test-alert-save:
	python -m scripts.test_alert_save

pipeline:
	python -m src.services.agent_pipeline

test-roster-sync:
	python -m src.services.roster_sync

test-transfermarkt:
	python -m src.services.transfermarkt_scraper

test-roster-update:
	python -m src.services.roster_update

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

