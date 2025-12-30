.PHONY: help setup test test-article test-player test-grok test-research init-db db-reset docker-up docker-down streamlit clean db-shell db-tables db-articles db-players pipeline pipeline-dry-run pipeline-fixtures test-roster-sync test-transfermarkt test-roster-update test-custom-tool test-bigquery test-pipeline test-pipeline-step1 test-pipeline-step2 test-pipeline-step4 test-pipeline-step6 test-pipeline-step6-dry test-alert-save prepare-rosters prepare-rosters-teams prepare-rosters-no-verify prepare-rosters-epl prepare-rosters-league test-fixture-list test-fixture-list-epl test-fixture test-fixture-dry test-fixture-index test-fixture-index-dry test-fixture-epl test-fixture-epl-dry check-roster roster-update-team roster-update-league

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
	@echo "  make test-alert-save - Test AlertService (save & query)"
	@echo "  make test-roster-sync - Test Roster sync service"
	@echo ""
	@echo "Pipeline:"
	@echo "  make pipeline          - Run full projection alert pipeline"
	@echo "  make pipeline-dry-run  - Run pipeline without writing to DB/BigQuery"
	@echo "  make pipeline-fixtures - Fetch and display fixtures only"
	@echo ""
	@echo "Roster Preparation:"
	@echo "  make prepare-rosters           - Full preparation (all leagues)"
	@echo "  make prepare-rosters-epl       - Premier League only"
	@echo "  make prepare-rosters-teams     - Only register missing teams"
	@echo "  make prepare-rosters-league LEAGUE='La Liga' - Specific league"
	@echo ""
	@echo "BigQuery:"
	@echo "  make test-bigquery     - Test BigQuery integration"
	@echo ""
	@echo "Pipeline Testing:"
	@echo "  make test-pipeline         - Test full pipeline flow"
	@echo "  make test-pipeline-step1   - Test fixture fetch only"
	@echo "  make test-pipeline-step2 FIXTURE='Team A vs Team B' - Test roster update"
	@echo "  make test-pipeline-step4 FIXTURE='Team A vs Team B' - Test agent pipeline"
	@echo ""
	@echo "Fixture-by-Fixture Pipeline (for troubleshooting):"
	@echo "  make test-fixture-list                    - List all fixtures"
	@echo "  make test-fixture-list-epl                - List Premier League fixtures only"
	@echo "  make test-fixture FIXTURE='Team A vs Team B'  - Run full pipeline for fixture"
	@echo "  make test-fixture-dry FIXTURE='Team A vs Team B' - Dry run (no BigQuery push)"
	@echo "  make test-fixture-index INDEX=0           - Run fixture by index"
	@echo "  make test-fixture-index-dry INDEX=0       - Dry run fixture by index"
	@echo "  make test-fixture-epl INDEX=0             - Run Premier League fixture by index"
	@echo "  make test-fixture-epl-dry INDEX=0         - Dry run Premier League fixture"
	@echo "  make test-pipeline-step6 FIXTURE='Team A vs Team B' - Test BigQuery enrichment"
	@echo "  make test-pipeline-step6-dry FIXTURE='Team A vs Team B' - Test enrichment (dry run)"
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

prepare-rosters:
	python -m src.services.roster_preparation

prepare-rosters-teams:
	python -m src.services.roster_preparation --teams-only

prepare-rosters-no-verify:
	python -m src.services.roster_preparation --skip-verify

prepare-rosters-epl:
	python -m src.services.roster_preparation --league "Premier League"

prepare-rosters-league:
	python -m src.services.roster_preparation --league "$(LEAGUE)"

test-bigquery:
	python -m scripts.test_bigquery

test-pipeline:
	python -m scripts.test_pipeline

test-pipeline-league:
	python -m scripts.test_pipeline --league "$(LEAGUE)"

test-pipeline-step1:
	python -m scripts.test_pipeline --step 1

test-pipeline-step2:
	python -m scripts.test_pipeline --step 2 --fixture "$(FIXTURE)"

test-pipeline-step4:
	python -m scripts.test_pipeline --step 4 --fixture "$(FIXTURE)"

test-pipeline-step6:
	python -m scripts.test_pipeline --step 6 --fixture "$(FIXTURE)"

test-pipeline-step6-dry:
	python -m scripts.test_pipeline --step 6 --fixture "$(FIXTURE)" --dry-run

# Full fixture pipeline testing (one fixture at a time)
test-fixture-list:
	python -m scripts.test_fixture_pipeline --list

test-fixture-list-epl:
	python -m scripts.test_fixture_pipeline --list --league "Premier League"

test-fixture:
	python -m scripts.test_fixture_pipeline --fixture "$(FIXTURE)"

test-fixture-dry:
	python -m scripts.test_fixture_pipeline --fixture "$(FIXTURE)" --dry-run

test-fixture-index:
	python -m scripts.test_fixture_pipeline --index $(INDEX)

test-fixture-index-dry:
	python -m scripts.test_fixture_pipeline --index $(INDEX) --dry-run

test-fixture-epl:
	python -m scripts.test_fixture_pipeline --index $(INDEX) --league "Premier League"

test-fixture-epl-dry:
	python -m scripts.test_fixture_pipeline --index $(INDEX) --league "Premier League" --dry-run

test-roster-sync:
	python -m src.services.roster_sync

# Quick roster check from database
# Usage: make check-roster TEAM="Manchester United" LEAGUE="Premier League"
check-roster:
	python -m scripts.check_roster "$(TEAM)" "$(LEAGUE)"

test-transfermarkt:
	python -m src.services.transfermarkt_scraper

test-roster-update:
	python -m src.services.roster_update

# Update roster for a specific team
# Usage: make roster-update-team TEAM="Arsenal" LEAGUE="Premier League"
roster-update-team:
	python -m src.services.roster_update --team "$(TEAM)" --league "$(LEAGUE)"

# Update rosters for all teams in a league
# Usage: make roster-update-league LEAGUE="Premier League"
roster-update-league:
	python -m src.services.roster_update --league "$(LEAGUE)"

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

