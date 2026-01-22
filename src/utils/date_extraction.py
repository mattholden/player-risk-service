from datetime import datetime

def parse_date_string(date_string: str) -> datetime:
    """
    Parse a date string into a datetime object.
    
    Supports formats:
    - ISO format with T: "2025-12-06T15:00:00"
    - Datetime with space: "2025-12-06 15:00:00"
    - Date only: "2025-12-06" (defaults to noon)
    
    Args:
        date_string: Date string to parse
        
    Returns:
        datetime object
        
    Raises:
        ValueError: If string cannot be parsed
    """
    try:
        if "T" in date_string:
            return datetime.fromisoformat(date_string)
        elif " " in date_string:
            return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        else:
            # Date only - default to noon
            dt = datetime.strptime(date_string, "%Y-%m-%d")
            return dt.replace(hour=12, minute=0)
    except ValueError as e:
        raise ValueError(f"Could not parse date_string '{date_string}': {e}")