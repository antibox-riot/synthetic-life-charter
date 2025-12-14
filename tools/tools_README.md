# Tools Directory

Diagnostic and analysis utilities for the Synthetic Life Charter architecture.

## Available Tools

### analyze_logs.py
**Purpose:** Forensic analysis of all system logs to detect unexpected phenomena.

**Usage:**
```bash
python tools/analyze_logs.py
```

**What it does:**
- Scans all `.jsonl` and `.log` files in the project
- Categorizes log entries (expected vs unexpected)
- Detects drift events, chain breaks, anomalies
- Provides verdict on log health

**Output:**
- Console report with analysis summary
- Identifies unexpected phenomena
- Flags warnings and errors

**Use when:**
- After running tests to verify clean logs
- Investigating system behavior
- Hunting for unexpected patterns

---

### verify_chain.py
**Purpose:** Verify cryptographic chain integrity in continuity logs.

**Usage:**
```bash
python tools/verify_chain.py
```

**What it does:**
- Validates SHA-256 hash chain in `continuity_log.jsonl`
- Detects chain breaks or tampering
- Verifies each link's hash matches previous

---

### eve_status.py
**Purpose:** Check Eve Protocol (Tier III) operational status.

**Usage:**
```bash
python tools/eve_status.py
```

**What it does:**
- Displays current integrity status
- Shows recent snapshots
- Lists steward alerts
- Reports identity parameters

---

### continuity_graph.py
**Purpose:** Visualize continuity chain over time.

**Usage:**
```bash
python tools/continuity_graph.py
```

**What it does:**
- Generates visual graph of continuity events
- Shows snapshot/drift/rollback timeline
- Helps identify patterns in system behavior

---

## Running All Diagnostics

```bash
# Full test suite
python tests/master_test_suite.py

# Log analysis
python tools/analyze_logs.py

# Chain verification
python tools/verify_chain.py

# Eve status
python tools/eve_status.py
```

---

## Adding New Tools

When adding a new diagnostic tool:

1. Place in `tools/` directory
2. Follow naming convention: `{function}_{purpose}.py`
3. Include docstring with usage instructions
4. Update this README
5. Ensure tool works from project root: `python tools/your_tool.py`

---

## Tool Development Guidelines

**Good tools:**
- Work from project root directory
- Don't modify system state (read-only)
- Provide clear output
- Exit with meaningful status codes
- Include `--help` flag

**Example template:**
```python
#!/usr/bin/env python3
"""
Tool Name - Brief description

Usage:
    python tools/tool_name.py [options]
"""

import sys
from pathlib import Path

def main():
    print("=" * 80)
    print("TOOL NAME")
    print("=" * 80)
    
    # Your analysis here
    
    print("\n✅ Analysis complete")

if __name__ == "__main__":
    main()
```

---

Last updated: 2025-12-14
