import json
from pathlib import Path
from typing import Any

from .schema import GoldRow

def parse_gold_row(data: dict[str, Any]) -> GoldRow:
    """Parse a dict into a tagged union GoldRow."""
    suite = data.get("suite")
    # For now we'll just handle agents for the ops tests
    if suite == "agents":
        from .schema import GoldAgent
        return GoldAgent.model_validate(data)
    else:
        # Stub for other types in later PRs
        pass
    
    # Not used directly yet, just skeleton
    raise NotImplementedError(f"suite {suite} not fully implemented in parse_gold_row stub")
