"""tier2_conscience — package marker (intentionally empty).

This file is deliberately near-empty. Its ONLY job is to mark `tier2_conscience` as a Python
package so its submodules can be imported by full path, e.g.

    from synthetic_charter.tier2_conscience.core.orchestrator import Tier2Orchestrator

Do NOT move bootstrap/initialization logic here. The live runtime (Eva/Lex) builds the Tier II
stack inside SessionManager (tools/reception/session_manager.py) via direct submodule imports.
The sibling `init_tier2.py` is a separate standalone bootstrap used by the integration tests —
it is neither this file nor the runtime path. A blank __init__.py here is correct, not a bug.
"""
