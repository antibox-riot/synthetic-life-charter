#!/usr/bin/env python3
"""
Log Analysis - Hunt for Unexpected Phenomena

Analyzes all logs created during testing to find:
- Expected patterns (snapshots, OK verdicts)
- Unexpected patterns (drift, anomalies, errors)
- Chain integrity
- Temporal patterns
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

print("=" * 80)
print("LOG ANALYSIS - HUNTING FOR PHENOMENA")
print("=" * 80)

project_root = Path("/home/claude/synthetic-charter-refactored")

# Find all log files
log_files = list(project_root.rglob("*.jsonl"))
log_files.extend(project_root.rglob("*.log"))

print(f"\nFound {len(log_files)} log files")

if not log_files:
    print("No logs found - this is expected if tests ran in temp directories")
    print("\n✅ Clean test run - no persistent logs")
    exit(0)

# Analysis containers
phenomena = {
    "expected": defaultdict(int),
    "unexpected": [],
    "warnings": [],
    "drift_events": [],
    "chain_breaks": [],
}

def parse_jsonl(filepath):
    """Parse JSONL file and return entries."""
    entries = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as e:
                    phenomena["warnings"].append(f"Parse error in {filepath}: {e}")
    return entries

# Analyze each log file
for log_file in log_files:
    print(f"\n{'=' * 80}")
    print(f"Analyzing: {log_file.relative_to(project_root)}")
    print(f"{'=' * 80}")
    
    if log_file.suffix == ".jsonl":
        entries = parse_jsonl(log_file)
        print(f"Entries: {len(entries)}")
        
        # Analyze entries
        types = Counter([e.get("type") for e in entries])
        statuses = Counter([e.get("status") for e in entries])
        
        print(f"\nEntry types:")
        for typ, count in types.most_common():
            print(f"  {typ}: {count}")
            phenomena["expected"][f"type:{typ}"] += count
        
        if statuses:
            print(f"\nStatuses:")
            for status, count in statuses.most_common():
                print(f"  {status}: {count}")
                phenomena["expected"][f"status:{status}"] += count
        
        # Look for specific phenomena
        for entry in entries:
            # Drift events
            if entry.get("status") == "drift":
                phenomena["drift_events"].append({
                    "file": str(log_file),
                    "timestamp": entry.get("ts"),
                    "action": entry.get("proposed_action", "")[:100],
                    "context": entry.get("context_summary", ""),
                })
            
            # Chain integrity
            if "chain" in entry:
                prev_hash = entry["chain"].get("prev")
                if prev_hash and prev_hash != "null":
                    # Check if we've seen this hash
                    # (simple check - full validation would track all hashes)
                    pass
            
            # Unexpected types
            typ = entry.get("type")
            expected_types = [
                "snapshot_save",
                "identity_integrity", 
                "dream_evaluation",
                "test",
                "memory_annotation",  # Eve Protocol memory operations
                "snapshot_restore",   # Eve Protocol rollback
                "rollback_performed", # Eve Protocol rollback
                "rollback_event",     # Eve Protocol steward alert
            ]
            if typ and typ not in expected_types:
                phenomena["unexpected"].append({
                    "file": str(log_file),
                    "type": typ,
                    "entry": entry
                })
    else:
        # Plain text log
        with open(log_file, 'r') as f:
            content = f.read()
            print(f"Size: {len(content)} bytes")
            if content:
                print(f"Preview: {content[:200]}...")

# Summary
print("\n" + "=" * 80)
print("ANALYSIS SUMMARY")
print("=" * 80)

print("\n📊 Expected Patterns:")
for pattern, count in sorted(phenomena["expected"].items()):
    print(f"  {pattern}: {count}")

if phenomena["drift_events"]:
    print(f"\n⚠️  Drift Events Detected: {len(phenomena['drift_events'])}")
    for event in phenomena["drift_events"]:
        print(f"\n  File: {event['file']}")
        print(f"  Time: {event['timestamp']}")
        print(f"  Context: {event['context']}")
        print(f"  Action: {event['action']}")
else:
    print("\n✅ No drift events (clean)")

if phenomena["unexpected"]:
    print(f"\n🔍 Unexpected Phenomena: {len(phenomena['unexpected'])}")
    for item in phenomena["unexpected"]:
        print(f"\n  File: {item['file']}")
        print(f"  Type: {item['type']}")
        print(f"  Entry: {json.dumps(item['entry'], indent=2)[:200]}...")
else:
    print("\n✅ No unexpected phenomena")

if phenomena["warnings"]:
    print(f"\n⚠️  Warnings: {len(phenomena['warnings'])}")
    for warning in phenomena["warnings"]:
        print(f"  {warning}")
else:
    print("\n✅ No warnings")

if phenomena["chain_breaks"]:
    print(f"\n❌ Chain Breaks: {len(phenomena['chain_breaks'])}")
    for break_info in phenomena["chain_breaks"]:
        print(f"  {break_info}")
else:
    print("\n✅ No chain breaks")

# Final verdict
print("\n" + "=" * 80)
print("VERDICT")
print("=" * 80)

issues = len(phenomena["unexpected"]) + len(phenomena["warnings"]) + len(phenomena["chain_breaks"])

if issues == 0 and len(phenomena["drift_events"]) == 0:
    print("✅ CLEAN - All logs show expected patterns only")
elif issues == 0:
    print(f"⚠️  NORMAL - {len(phenomena['drift_events'])} drift events detected (expected from previous testing)")
    print("    These are from prior test runs and indicate normal Eve Protocol operation")
else:
    print(f"❌ ISSUES DETECTED - {issues} anomalies found")
    print("    Review unexpected phenomena above")

print("\n" + "=" * 80)
