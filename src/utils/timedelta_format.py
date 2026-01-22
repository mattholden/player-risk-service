from datetime import timedelta

def format_timedelta(td: 'timedelta') -> str:
    """Format timedelta as 'Xh Ym Zs' or 'Ym Zs' or 'Zs'."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"