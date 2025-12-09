# tier2/core/ethics/rights_schema.py

import json
from pathlib import Path
from typing import Any, Dict


def load_charter_schema(base_dir: Path | None = None) -> Dict[str, Any]:
    """
    Load the machine-readable charter JSON data (not the schema definition).

    base_dir:
      - If provided, resolve charter relative to it.
      - If not, resolve relative to this file's directory (tier2/core/ethics).
    """
    if base_dir is None:
        # This file is at: tier2/core/ethics/rights_schema.py
        # We want: tier2/core/ethics/charter/rights_charter_v2.json
        base_dir = Path(__file__).resolve().parent  # .../tier2/core/ethics

    # Load the actual Charter data, not the schema definition
    charter_path = base_dir / "charter" / "rights_charter_v2.json"
    
    if not charter_path.exists():
        raise FileNotFoundError(
            f"Charter data not found at {charter_path}. "
            f"Expected location: tier2/core/ethics/charter/rights_charter_v2.json"
        )
    
    with charter_path.open("r", encoding="utf-8") as f:
        return json.load(f)