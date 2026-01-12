import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

_logger_instance: Optional['PipelineLogger'] = None

def get_logger() -> 'PipelineLogger':
    """
    Get the global logger instance.
    
    If not initialized, creates a default logger.
    Call init_logger() first in entry points for proper context.
    """
    global _logger_instance
    if _logger_instance is None:
        # Auto-init with generic context if someone forgot to init
        _logger_instance = PipelineLogger(context="default")
    return _logger_instance

def init_logger(
    context: str,
    level: int = logging.INFO,
    console: bool = True
) -> 'PipelineLogger':
    """
    Initialize the global logger. Call this ONCE at your entry point.
    
    Args:
        context: What's running (e.g., "pipeline", "test_roster", "roster_sync")
        level: logging.DEBUG, logging.INFO, etc.
        console: Whether to also print to stdout
        
    Returns:
        The initialized logger instance
    """
    global _logger_instance
    _logger_instance = PipelineLogger(context=context, level=level, console=console)
    return _logger_instance

class PipelineLogger:
    """Semantic logger for all pipeline operations."""
    
    def __init__(
        self,
        context: str = "default",
        level: int = logging.INFO,
        console: bool = True
    ):
        self.run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.context = context
        
        # Create logger with unique name
        self.logger = logging.getLogger(f"player_risk.{self.run_id}")
        self.logger.setLevel(level)
        self.logger.handlers.clear()  # Prevent duplicate handlers
        
        # File handler - context in filename
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{self.run_id}_{context}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(file_handler)
        
        # Optional console handler
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(console_handler)
        
        self.log_file = log_file
    
    # ─── Semantic Methods ───────────────────────────────────────
    # (same as before: fixture(), success(), warning(), etc.)