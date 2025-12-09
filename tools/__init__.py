"""
Tier III Operational Tools

Monitoring and diagnostic utilities for the Eve Protocol (Tier III).

Created by: Ryu (Anti-Box Riot Collective)
Purpose: Operational visibility and health monitoring

Tools:
  - verify_chain: Quick integrity check (CI/CD friendly)
  - eve_status: Comprehensive status dashboard
  - continuity_graph: Timeline visualization and DOT export

Usage:
  python -m tools.verify_chain
  python -m tools.eve_status
  python -m tools.continuity_graph [--dot output.dot]
"""

__version__ = "1.0.0"
__author__ = "Anti-Box Riot Collective"

# Make tools importable
from . import verify_chain
from . import eve_status
from . import continuity_graph

__all__ = ["verify_chain", "eve_status", "continuity_graph"]
