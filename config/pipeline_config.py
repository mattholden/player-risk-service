from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class PipelineConfig:
    """Configuration for the ProjectionAlertPipeline."""
    dry_run: bool = False
    fixtures_only: bool = False
    leagues: list[str] | str | None = None
    push_all: bool = True
    verbose: bool = False
    
    @classmethod
    def from_file(cls, path: str | Path = "config/pipeline_config.json") -> "PipelineConfig":
        """Load config from a JSON file."""
        config_path = Path(path)
        if not config_path.exists():
            print(f"⚠️  Config file not found at {config_path}, using defaults")
            return cls()
        
        with open(config_path) as f:
            data = json.load(f)
        
        return cls(**data)