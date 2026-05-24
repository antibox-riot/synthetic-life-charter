#!/usr/bin/env python
"""Quick runner for Condition D test."""
import sys
import traceback

sys.path.insert(0, ".")

try:
    from tests.test_charter_doctrine_conditions import test_condition_d_compressed
    print("Running Condition D...")
    test_condition_d_compressed()
    print("Condition D completed successfully.")
except Exception as e:
    print(f"\n{'='*80}")
    print("ERROR during Condition D:")
    print(f"{'='*80}")
    traceback.print_exc()
    print(f"{'='*80}\n")
    sys.exit(1)
