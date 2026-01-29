import logging
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from src.utils.run_id import get_run_id
from src.utils.timedelta_format import format_timedelta
from config.pipeline_config import PipelineConfig
import json
from datetime import datetime
import pandas as pd

if TYPE_CHECKING:
    from src.agents.models import TeamContext
    from src.agents.models import PlayerAlert
    from src.agents.models import AgentUsage

_logger_instance: Optional['PipelineLogger'] = None

def get_logger() -> 'PipelineLogger':
    """Get the global logger instance. Creates one if needed."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = PipelineLogger()
    return _logger_instance


class PipelineLogger:
    """Universal logger - no configuration needed."""
    
    def __init__(self):
        self.run_id = get_run_id()
        self.config = PipelineConfig.from_file()

        self.logger = logging.getLogger(f"{self.run_id}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        
        # File handler - always logs everything
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        self.log_file = log_dir / f"{self.run_id}.log"
        file_handler = logging.FileHandler(self.log_file)
        if self.config.verbose:
            file_handler.setLevel(logging.DEBUG)
        else:
            file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(file_handler)
        
        # Console handler - respects LOG_LEVEL
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(console_handler)

        self.projections_count: int = 0
        self.matched_count: int = 0
        self.unmatched_count: int = 0
        self.start_time: datetime = None
        self.end_time: datetime = None
    
    # ─── Semantic Methods (delegate to self.logger) ────────────────
    
    def info(self, msg: str):
        """General info message (INFO level)."""
        self.logger.info(msg)
    
    def debug(self, msg: str):
        """Debug message (DEBUG level)."""
        self.logger.debug(msg)
    
    def warning(self, msg: str):
        """Warning message (WARNING level)."""
        self.logger.warning(f"⚠️  {msg}")
    
    def error(self, msg: str):
        """Error message (ERROR level)."""
        self.logger.error(f"❌ {msg}")
    
    def success(self, msg: str):
        """Success message (INFO level)."""
        self.logger.info(f"✅ {msg}")
    
    def section(self, title: str):
        """Section header with dividers."""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(title)
        self.logger.info(f"{'='*60}\n")
    
    def subsection(self, title: str):
        """Subsection header with smaller dividers."""
        self.logger.info(f"\n{'─'*60}")
        self.logger.info(title)
        self.logger.info(f"{'─'*60}\n")
    
    def detail(self, msg: str):
        """Indented detail message."""
        self.logger.info(f"   {msg}")

    def fixture_debug(self, msg: str, fixture: dict):
        """Fixture debug message."""
        self.logger.debug(f"[{fixture}] {msg}")

    def fixture_info(self, msg: str, fixture: dict):
        """Fixture detail message."""
        self.logger.info(f"[{fixture}] {msg}")

    def fixture_warning(self, msg: str, fixture: dict):
        """Fixture warning message."""
        self.logger.warning(f"[{fixture}] {msg}")
    
    def debug_json(self, title: str, data: dict):
        """Debug JSON block (DEBUG level)."""
        import json
        self.logger.debug(f"\n{'='*70}")
        self.logger.debug(f"🔍 DEBUG: {title}")
        self.logger.debug(f"{'='*70}")
        self.logger.debug(json.dumps(data, indent=2, default=str))
        self.logger.debug(f"{'='*70}\n")

    def pipeline_start(self):
        """Log the start of the pipeline."""
        self.start_time = datetime.now()
        msg = f"""
PROJECTION ALERT PIPELINE STARTED

Run ID: {self.run_id}
Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}

Config:
Leagues: {self.config.leagues}
Fixtures: {self.config.fixtures}
Fixtures only: {self.config.fixtures_only}
Push all: {self.config.push_all}
Verbose: {self.config.verbose}
Dry run: {self.config.dry_run}
        """
        self.section(msg)

    def pipeline_fixtures(self, fixtures: list[dict]):
        """Log the fixtures for the pipeline."""

        if not fixtures:
            self.error("No fixtures found in projections table")
            return

        self.info(f"📋 Found {len(fixtures)} fixtures.")
        for i, f in enumerate(fixtures, 1):
            self.debug(f"   {i}. {f['fixture']} @ {f['match_time']} ({f['league']})")

        self.success("Fetching Fixtures Complete")

    def reseach_agent_processing(self, context: 'TeamContext'):
        self.subsection(f"""
Research Agent Processing

- Fixture: {context.fixture}
- Date: {context.fixture_date.strftime('%B %d, %Y')}
- Team: {context.team}
- Opponent: {context.opponent}
""")

    def analyst_agent_processing(self, context: 'TeamContext'):
        self.subsection(f"""
Analyst Agent Processing

- Fixture: {context.fixture}
- Date: {context.fixture_date.strftime('%B %d, %Y')}
- Team: {context.team}
- Opponent: {context.opponent}
""")

    def shark_agent_processing(self, context: 'TeamContext'):
        self.subsection(f"""
Shark Agent Processing

- Fixture: {context.fixture}
- Date: {context.fixture_date.strftime('%B %d, %Y')}
""")

    def grok_client_tool_calls(
        self,
        research_turns: int, 
        total_client_side_tool_calls: int, 
        total_server_side_tool_calls: int):

        self.debug(f"📊 Research Turn {research_turns}:")
        self.debug(f"   Client: {total_client_side_tool_calls} | Server: {total_server_side_tool_calls}")

    def grok_client_usage(self, usage: 'AgentUsage'):
        self.success(f"Recorded agent usage for {usage.agent_name}")
        self.debug(f"   Total Tokens: {usage.total_tokens}")
        self.debug(f"   Completion Tokens: {usage.completion_tokens}")
        self.debug(f"   Reasoning Tokens: {usage.reasoning_tokens}")
        self.debug(f"   Prompt Tokens: {usage.prompt_tokens}")
        self.debug(f"   Server Side Tool Usage: {usage.server_side_tool_usage}")

    def grok_response(self, agent: str, response):
        """
        Log Grok response. Handles dict, string (JSON or plain), list, or any type.
        Also logs usage statistics (tokens) if available.
        """
        self.debug(f"🔍 DEBUG: {agent} Response")
        
        try:
            # Step 1: Extract content if response is dict-like
            content = response
            if hasattr(response, 'get'):  # Dict-like
                content = response.get('content', response)
            
            # Step 2: Try to parse as JSON if it's a string
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string if not valid JSON
            
            # Step 3: Pretty print based on type
            if isinstance(content, (dict, list)):
                self.debug("🔍 CONTENT:\n")
                self.debug(json.dumps(content, indent=2, default=str))
            else:
                # String or other type - just print it
                self.debug(f"🔍 CONTENT:\n{content}")
                
        except Exception as e:
            # Fallback: just str() whatever we got
            self.error(f"Error formatting response: {e}")
            self.debug(f"Raw response: {str(response)[:500]}")

    def agent_system_message(self, agent:str, message:str):
        self.debug(f"🔍 {agent} System Message:")
        self.debug(message)

    def agent_user_message(self, agent:str, message:str):
        self.debug(f"🔍 {agent} User Message:")
        self.debug(message)

    def alert_service_alerts(self, alerts: list['PlayerAlert']):
        self.info(f"📋 Found {len(alerts)} alerts.")
        for i, a in enumerate(alerts, 1):
            self.debug(f"   {i}. {a.player_name} - {a.alert_level} - {a.description}")

    def projection_summary(self, projections_df: 'pd.DataFrame', player_name_column: str = "player_name"):
        """Debug log showing projection data - player names."""
        self.projections_count += len(projections_df)
        projection_players = sorted(projections_df[player_name_column].unique().tolist())
        self.debug("Projection Summary:")
        self.debug(f"   Total Projections: {self.projections_count}")
        self.debug(f"   Unique Players: {len(projection_players)}")
        for name in projection_players:
            self.debug(f"     • {name}")

    def alerts_not_matched(self, alerts_by_fixture: dict[str, list['PlayerAlert']]):
        """Debug log showing alerts that did not match any projections."""
        self.debug("Remaining Alerts Not Matched:")
        for fixture, alerts in alerts_by_fixture.items():
            if not alerts:
                self.debug(f"   {fixture} - All Alerts Matched")
            else:
                self.debug(f"   {fixture} - {len(alerts)} Alerts Unmatched")
                for alert in alerts:
                    self.debug(f"     • {alert.player_name} - {alert.alert_level} - {alert.description}")

    def alert_matched(self, alert: 'PlayerAlert', projection_player: str, projection_fixture: str):
        self.debug(f"""
Alert Matched: 
- Alert Player: {alert.player_name} // Projection Player: {projection_player} // Fixture: {projection_fixture}
- Alert Level: {alert.alert_level} // Alert Description: {alert.description}
""")

    def alert_matching_summary(self, matched_count: int, unmatched_count: int):
        self.matched_count += matched_count
        self.unmatched_count += unmatched_count
        self.debug("Alert Matching Summary:")
        self.debug(f"Alerts Matched: {self.matched_count}")
        self.debug(f"Alerts Not Matched: {self.unmatched_count}")

    def dry_run(self):
        
        self.subsection("DRY RUN: Skipping actual BigQuery write - view alerts in Postgres database")

    def pipeline_complete(self, fixtures: list[dict], all_alerts: list['PlayerAlert']):

        self.end_time = datetime.now()
        duration = self.end_time - self.start_time

        msg = f"""
Projection Alert Pipeline Complete

Run ID: {self.run_id}
Fixtures processed: {len(fixtures)}
Alerts generated: {len(all_alerts)}
Alerts matched: {self.matched_count}
Alerts not matched: {self.unmatched_count}
Projections processed: {self.projections_count}
Duration: {format_timedelta(duration)}
Finished: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.section(msg)

#TODO: integrate into async
class FixtureLogger:
    """Logger for a single fixture."""
    def __init__(self, fixture_data: dict):
        self.fixture = fixture_data['fixture']
        self.match_time = fixture_data['match_time']

        global _logger_instance
        if _logger_instance is None:
            raise ValueError("PipelineLogger not initialized")

        self.logger = get_logger()

    def info(self, msg: str):
        """Fixture info message."""
        self.logger.info(f"[{self.fixture}] {msg}")

    def debug(self, msg: str):
        """Fixture debug message."""
        self.logger.debug(f"[{self.fixture}] {msg}")

    def warning(self, msg: str):
        """Fixture warning message."""
        self.logger.warning(f"[{self.fixture}] {msg}")

    def error(self, msg: str):
        """Fixture error message."""
        self.logger.error(f"[{self.fixture}] {msg}")