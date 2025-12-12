.PHONY: help setup test test-article test-player test-grok test-research init-db db-reset docker-up docker-down streamlit clean db-shell db-tables db-articles db-players pipeline pipeline-dry-run pipeline-fixtures test-roster-sync test-transfermarkt test-roster-update test-custom-tool test-bigquery

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
	@echo "  make pipeline          - Run full projection alert pipeline"
	@echo "  make pipeline-dry-run  - Run pipeline without writing to DB/BigQuery"
	@echo "  make pipeline-fixtures - Fetch and display fixtures only"
	@echo ""
	@echo "BigQuery:"
	@echo "  make test-bigquery     - Test BigQuery integration"
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
	python -m src.pipeline

pipeline-dry-run:
	python -m src.pipeline --dry-run

pipeline-fixtures:
	python -m src.pipeline --fixtures-only

test-bigquery:
	python -m scripts.test_bigquery

test-roster-sync:
	python -m src.services.roster_sync

test-transfermarkt:
	python -m src.services.transfermarkt_scraper

test-roster-update:
	python -m src.services.roster_update

test-custom-tool:
	python -m scripts.test_custom_tool

test-roster-tool:
	python -m scripts.test_roster_tool

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

db-teams:
	@echo "Teams in database:"
	@docker-compose exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "SELECT id, team_name, league, transfermarkt_id, transfermarkt_slug, is_active FROM teams ORDER BY league, team_name;"

# Team lookup - search Transfermarkt for team data
# Usage: make team-lookup TEAM="Manchester City" LEAGUE="Premier League"
team-lookup:
	python -m src.services.team_lookup "$(TEAM)" "$(LEAGUE)"

# Team lookup and save to database
# Usage: make team-add TEAM="Manchester City" LEAGUE="Premier League"
team-add:
	python -m src.services.team_lookup "$(TEAM)" "$(LEAGUE)" --save

