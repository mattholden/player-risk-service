import logging
import os
from pathlib import Path
from typing import Optional
from src.utils.run_id import get_run_id

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
        
        self.logger = logging.getLogger(f"{self.run_id}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        
        # File handler - always logs everything
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        self.log_file = log_dir / f"{self.run_id}.log"
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.DEBUG)  # File gets ALL messages
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(file_handler)
        
        # Console handler - respects LOG_LEVEL
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(console_handler)
    
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
    
    def debug_json(self, title: str, data: dict):
        """Debug JSON block (DEBUG level)."""
        import json
        self.logger.debug(f"\n{'='*70}")
        self.logger.debug(f"🔍 DEBUG: {title}")
        self.logger.debug(f"{'='*70}")
        self.logger.debug(json.dumps(data, indent=2, default=str))
        self.logger.debug(f"{'='*70}\n")

    def pipeline_fixtures(self, fixtures: list[dict]):
        """Log the fixtures for the pipeline."""

        if not fixtures:
            self.error("No fixtures found in projections table")
            return

        self.info(f"📋 Found {len(fixtures)} fixtures.")
        for i, f in enumerate(fixtures, 1):
            self.debug(f"   {i}. {f['fixture']} @ {f['match_time']} ({f['league']})")

        self.success("Fetching Fixtures Complete")