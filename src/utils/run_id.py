from datetime import datetime

_run_id: str = None


def get_run_id() -> str:
    """
    Get or create the current run ID.
    
    First call creates it. All subsequent calls return the same value.
    Used by logger (file naming) and pipeline (alert tracking).
    """
    global _run_id
    if _run_id is None:
        _run_id = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    return _run_id
