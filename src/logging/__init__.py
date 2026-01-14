"""
Logging package - Universal pipeline logger.

Usage:
    from src.logging import get_logger
    
    logger = get_logger()
    logger.info("Starting pipeline...")
    logger.success("Completed!")
"""

from src.logging.logger import get_logger, PipelineLogger

__all__ = [
    "get_logger",
    "PipelineLogger",
]

