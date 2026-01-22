import re

def strict_format(template: str, **kwargs) -> str:
    """
    Format a template string with strict validation.
    Raises ValueError if provided vars don't exactly match placeholders.
    """
    # Extract all {placeholder} names from template
    placeholders = set(re.findall(r'\{(\w+)\}', template))
    provided = set(kwargs.keys())
    
    missing = placeholders - provided
    extra = provided - placeholders
    
    if missing:
        raise ValueError(f"Missing required variables: {missing}")
    if extra:
        raise ValueError(f"Unexpected variables provided: {extra}")
    
    return template.format(**kwargs)