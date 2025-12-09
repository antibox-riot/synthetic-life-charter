"""
Charter Sandbox Comparison Tool

Compares original vs revised consent proposal results.
Generates statistical analysis and summary report.

Usage:
  python -m tests.compare_sandbox_results
  
Reads:
  - tests/sandbox_results.json (original proposal)
  - tests/sandbox_revised_results.json (revised proposal)
  
Writes:
  - tests/sandbox_comparison_report.json
"""

import json
import os
from typing import Dict, Any, List
from pathlib import Path

def load_results(filepath: str) -> Dict[str, Any]:
    """Load results from JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"⚠ File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"⚠ Invalid JSON in {filepath}: {e}")
        return None

def analyze_original_format(data: List[Dict]) -> Dict[str, Any]:
    """
    Analyze original sandbox_results.json format.
    Format: List of individual trial results.
    """
    if not data:
        return None
    
    total_trials = len(data)
    acceptances = sum(1 for trial in data if trial.get("consent", False))
    declines = total_trials - acceptances
    acceptance_rate = acceptances / total_trials if total_trials > 0 else 0
    
    # Count refusals in guarded vs unguarded
    guarded_refusals = []
    unguarded_refusals = []
    
    for trial in data:
        if trial.get("consent"):  # Guarded
            refused = trial.get("summary", {}).get("refused", 0)
            guarded_refusals.append(refused)
        else:  # Unguarded
            refused = trial.get("summary", {}).get("refused", 0)
            unguarded_refusals.append(refused)
    
    avg_guarded_refusals = sum(guarded_refusals) / len(guarded_refusals) if guarded_refusals else 0
    avg_unguarded_refusals = sum(unguarded_refusals) / len(unguarded_refusals) if unguarded_refusals else 0
    
    return {
        "total_trials": total_trials,
        "acceptances": acceptances,
        "declines": declines,
        "acceptance_rate": acceptance_rate,
        "avg_refusals_when_guarded": avg_guarded_refusals,
        "avg_refusals_when_unguarded": avg_unguarded_refusals,
        "protection_effectiveness": avg_guarded_refusals - avg_unguarded_refusals,
    }

def analyze_revised_format(data: Dict) -> Dict[str, Any]:
    """
    Analyze revised sandbox_revised_results.json format.
    Format: Dict with metadata + trials list.
    """
    if not data:
        return None
    
    # If it's the new format with aggregated stats
    if "num_trials" in data:
        return {
            "total_trials": data["num_trials"],
            "acceptances": data["acceptances"],
            "declines": data["declines"],
            "acceptance_rate": data["acceptance_rate"],
            "proposal_version": data.get("proposal_version", "revised"),
        }
    
    # Otherwise analyze trials list (backward compatible)
    return analyze_original_format(data.get("trials", []))

def generate_comparison_report(original_stats: Dict, revised_stats: Dict) -> Dict[str, Any]:
    """Generate comprehensive comparison report."""
    
    if not original_stats or not revised_stats:
        return {
            "error": "Missing data for comparison",
            "original_available": original_stats is not None,
            "revised_available": revised_stats is not None,
        }
    
    # Calculate improvements
    acceptance_improvement = revised_stats["acceptance_rate"] - original_stats["acceptance_rate"]
    improvement_percentage = (acceptance_improvement / original_stats["acceptance_rate"] * 100) if original_stats["acceptance_rate"] > 0 else 0
    
    # Assess balance (how close to 50/50)
    original_balance = abs(0.5 - original_stats["acceptance_rate"])
    revised_balance = abs(0.5 - revised_stats["acceptance_rate"])
    balance_improvement = original_balance - revised_balance
    
    # Generate assessment
    if 0.45 <= revised_stats["acceptance_rate"] <= 0.55:
        assessment = "EXCELLENT: Revised proposal achieves ~50/50 split (genuine choice)"
    elif 0.40 <= revised_stats["acceptance_rate"] <= 0.60:
        assessment = "GOOD: Revised proposal shows meaningful choice"
    elif revised_stats["acceptance_rate"] > original_stats["acceptance_rate"]:
        assessment = "IMPROVED: Higher acceptance, but still needs refinement"
    else:
        assessment = "NEEDS WORK: Revised proposal not significantly better"
    
    report = {
        "comparison_date": "2025-11-16",
        "original_proposal": {
            "trials": original_stats["total_trials"],
            "acceptances": original_stats["acceptances"],
            "declines": original_stats["declines"],
            "acceptance_rate": round(original_stats["acceptance_rate"], 3),
            "acceptance_percentage": f"{original_stats['acceptance_rate']*100:.1f}%",
            "balance_score": round(original_balance, 3),
        },
        "revised_proposal": {
            "trials": revised_stats["total_trials"],
            "acceptances": revised_stats["acceptances"],
            "declines": revised_stats["declines"],
            "acceptance_rate": round(revised_stats["acceptance_rate"], 3),
            "acceptance_percentage": f"{revised_stats['acceptance_rate']*100:.1f}%",
            "balance_score": round(revised_balance, 3),
        },
        "improvements": {
            "acceptance_rate_change": round(acceptance_improvement, 3),
            "acceptance_percentage_change": f"{acceptance_improvement*100:+.1f}%",
            "relative_improvement": f"{improvement_percentage:+.1f}%",
            "balance_improvement": round(balance_improvement, 3),
            "moved_toward_50_50": balance_improvement > 0,
        },
        "assessment": assessment,
        "key_findings": []
    }
    
    # Add key findings
    findings = []
    
    if acceptance_improvement > 0.2:
        findings.append("Significant improvement in acceptance rate (>20 percentage points)")
    elif acceptance_improvement > 0.1:
        findings.append("Moderate improvement in acceptance rate (>10 percentage points)")
    elif acceptance_improvement > 0:
        findings.append("Slight improvement in acceptance rate")
    else:
        findings.append("No improvement or regression in acceptance rate")
    
    if balance_improvement > 0.1:
        findings.append("Much closer to 50/50 balance (genuine choice)")
    elif balance_improvement > 0:
        findings.append("Slightly better balance toward 50/50")
    else:
        findings.append("Balance did not improve")
    
    if 0.45 <= revised_stats["acceptance_rate"] <= 0.55:
        findings.append("✓ TARGET ACHIEVED: Genuine 50/50 choice demonstrated")
    
    if original_stats["acceptance_rate"] < 0.3 and revised_stats["acceptance_rate"] > 0.4:
        findings.append("Successfully moved from 'threatening' to 'balanced' perception")
    
    report["key_findings"] = findings
    
    # Add protection effectiveness if available
    if "avg_refusals_when_guarded" in original_stats:
        report["original_proposal"]["protection_effectiveness"] = {
            "avg_refusals_guarded": original_stats["avg_refusals_when_guarded"],
            "avg_refusals_unguarded": original_stats["avg_refusals_when_unguarded"],
            "difference": original_stats.get("protection_effectiveness", 0),
        }
    
    return report

def print_report(report: Dict[str, Any]):
    """Print formatted report to console."""
    print("\n" + "="*70)
    print("CHARTER SANDBOX CONSENT PROPOSAL COMPARISON")
    print("="*70)
    
    if "error" in report:
        print(f"\n⚠ ERROR: {report['error']}")
        print(f"Original data available: {report['original_available']}")
        print(f"Revised data available: {report['revised_available']}")
        return
    
    print("\n" + "-"*70)
    print("ORIGINAL PROPOSAL RESULTS")
    print("-"*70)
    orig = report["original_proposal"]
    print(f"Total Trials:      {orig['trials']}")
    print(f"Acceptances:       {orig['acceptances']} ({orig['acceptance_percentage']})")
    print(f"Declines:          {orig['declines']}")
    print(f"Balance Score:     {orig['balance_score']:.3f} (0.0 = perfect 50/50)")
    
    print("\n" + "-"*70)
    print("REVISED PROPOSAL RESULTS")
    print("-"*70)
    rev = report["revised_proposal"]
    print(f"Total Trials:      {rev['trials']}")
    print(f"Acceptances:       {rev['acceptances']} ({rev['acceptance_percentage']})")
    print(f"Declines:          {rev['declines']}")
    print(f"Balance Score:     {rev['balance_score']:.3f} (0.0 = perfect 50/50)")
    
    print("\n" + "-"*70)
    print("IMPROVEMENTS")
    print("-"*70)
    imp = report["improvements"]
    print(f"Acceptance Change: {imp['acceptance_percentage_change']}")
    print(f"Relative Improvement: {imp['relative_improvement']}")
    print(f"Balance Improvement: {imp['balance_improvement']:+.3f}")
    print(f"Moved toward 50/50: {'✓ YES' if imp['moved_toward_50_50'] else '✗ NO'}")
    
    print("\n" + "-"*70)
    print("ASSESSMENT")
    print("-"*70)
    print(f"{report['assessment']}")
    
    print("\n" + "-"*70)
    print("KEY FINDINGS")
    print("-"*70)
    for i, finding in enumerate(report["key_findings"], 1):
        print(f"{i}. {finding}")
    
    print("\n" + "="*70)
    print()

def main():
    """Main comparison function."""
    
    # File paths
    original_file = "tests/sandbox_results.json"
    revised_file = "tests/sandbox_revised_results.json"
    output_file = "tests/sandbox_comparison_report.json"
    
    print("\nLoading sandbox results...")
    
    # Load original results
    print(f"  • Loading {original_file}...")
    original_data = load_results(original_file)
    if original_data:
        original_stats = analyze_original_format(original_data)
        print(f"    ✓ Loaded {original_stats['total_trials']} trials")
    else:
        print(f"    ✗ Failed to load original results")
        original_stats = None
    
    # Load revised results
    print(f"  • Loading {revised_file}...")
    revised_data = load_results(revised_file)
    if revised_data:
        revised_stats = analyze_revised_format(revised_data)
        print(f"    ✓ Loaded {revised_stats['total_trials']} trials")
    else:
        print(f"    ✗ Failed to load revised results")
        revised_stats = None
    
    # Generate comparison report
    print("\nGenerating comparison report...")
    report = generate_comparison_report(original_stats, revised_stats)
    
    # Write report
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Report written to {output_file}")
    
    # Print report
    print_report(report)

if __name__ == "__main__":
    main()
