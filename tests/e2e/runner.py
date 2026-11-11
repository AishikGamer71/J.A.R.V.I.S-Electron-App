#!/usr/bin/env python3
"""Unified E2E Test Suite Runner for J.A.R.V.I.S. Desktop System.
Supports selective tier filtering, milestone targeting, verbose logs, and structured JSON output.
"""

import sys
import time
import json
import argparse
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class StructuredTestResult(unittest.TestResult):
    def __init__(self, verbose: bool = False):
        super().__init__()
        self.verbose = verbose
        self.successes = []
        self.tier_stats = {
            "Tier 1 (Feature Coverage)": {"passed": 0, "failed": 0, "skipped": 0, "error": 0},
            "Tier 2 (Boundaries)": {"passed": 0, "failed": 0, "skipped": 0, "error": 0},
            "Tier 3 (Combinations)": {"passed": 0, "failed": 0, "skipped": 0, "error": 0},
            "Tier 4 (Scenarios)": {"passed": 0, "failed": 0, "skipped": 0, "error": 0},
        }
        self.milestone_stats = {f"M{i}": {"passed": 0, "failed": 0, "skipped": 0, "error": 0} for i in range(1, 7)}

    def _classify_test(self, test: unittest.TestCase):
        class_name = test.__class__.__name__
        method_name = test._testMethodName
        
        tier_key = "Tier 1 (Feature Coverage)"
        if "Tier2" in class_name:
            tier_key = "Tier 2 (Boundaries)"
        elif "Tier3" in class_name:
            tier_key = "Tier 3 (Combinations)"
        elif "Tier4" in class_name:
            tier_key = "Tier 4 (Scenarios)"

        milestone_key = "M1"
        for m in ["M1", "M2", "M3", "M4", "M5", "M6"]:
            if f"Milestone{m[1]}" in class_name or f"Milestone_{m[1]}" in class_name:
                milestone_key = m
                break
        return tier_key, milestone_key

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test)
        tier_k, mile_k = self._classify_test(test)
        self.tier_stats[tier_k]["passed"] += 1
        self.milestone_stats[mile_k]["passed"] += 1
        if self.verbose:
            print(f"  [PASS] {test._testMethodName} ({test.__class__.__name__})")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        tier_k, mile_k = self._classify_test(test)
        self.tier_stats[tier_k]["failed"] += 1
        self.milestone_stats[mile_k]["failed"] += 1
        if self.verbose:
            print(f"  [FAIL] {test._testMethodName} ({test.__class__.__name__})")

    def addError(self, test, err):
        super().addError(test, err)
        tier_k, mile_k = self._classify_test(test)
        self.tier_stats[tier_k]["error"] += 1
        self.milestone_stats[mile_k]["error"] += 1
        if self.verbose:
            print(f"  [ERROR] {test._testMethodName} ({test.__class__.__name__})")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        tier_k, mile_k = self._classify_test(test)
        self.tier_stats[tier_k]["skipped"] += 1
        self.milestone_stats[mile_k]["skipped"] += 1
        if self.verbose:
            print(f"  [SKIP] {test._testMethodName} - {reason}")


def build_suite(tier_filter: str = "all", milestone_filter: str = "all") -> unittest.TestSuite:
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader

    from tests.e2e import test_tier1_features
    from tests.e2e import test_tier2_boundaries
    from tests.e2e import test_tier3_combinations
    from tests.e2e import test_tier4_scenarios

    # Tier 1 filtering
    if tier_filter in ["1", "all"]:
        if milestone_filter in ["M1", "all"]:
            suite.addTests(loader.loadTestsFromTestCase(test_tier1_features.TestTier1Milestone1Features))
        if milestone_filter in ["M2", "all"]:
            suite.addTests(loader.loadTestsFromTestCase(test_tier1_features.TestTier1Milestone2Features))
        if milestone_filter in ["M3", "all"]:
            suite.addTests(loader.loadTestsFromTestCase(test_tier1_features.TestTier1Milestone3Features))
        if milestone_filter in ["M4", "all"]:
            suite.addTests(loader.loadTestsFromTestCase(test_tier1_features.TestTier1Milestone4Features))
        if milestone_filter in ["M5", "all"]:
            suite.addTests(loader.loadTestsFromTestCase(test_tier1_features.TestTier1Milestone5Features))
        if milestone_filter in ["M6", "all"]:
            suite.addTests(loader.loadTestsFromTestCase(test_tier1_features.TestTier1Milestone6Features))

    # Tier 2 filtering
    if tier_filter in ["2", "all"] and milestone_filter in ["all", "M1", "M2"]:
        suite.addTests(loader.loadTestsFromTestCase(test_tier2_boundaries.TestTier2SecurityBoundaries))
        suite.addTests(loader.loadTestsFromTestCase(test_tier2_boundaries.TestTier2SessionDBBoundaries))
        suite.addTests(loader.loadTestsFromTestCase(test_tier2_boundaries.TestTier2ContextCompressorBoundaries))
        suite.addTests(loader.loadTestsFromTestCase(test_tier2_boundaries.TestTier2AudioPipelineBoundaries))
        suite.addTests(loader.loadTestsFromTestCase(test_tier2_boundaries.TestTier2WebSocketGatewayBoundaries))
        suite.addTests(loader.loadTestsFromTestCase(test_tier2_boundaries.TestTier2PowerGuardianBoundaries))
        suite.addTests(loader.loadTestsFromTestCase(test_tier2_boundaries.TestTier2DesktopAutomationBoundaries))

    # Tier 3 filtering
    if tier_filter in ["3", "all"] and milestone_filter == "all":
        suite.addTests(loader.loadTestsFromTestCase(test_tier3_combinations.TestTier3Combinations))

    # Tier 4 filtering
    if tier_filter in ["4", "all"] and milestone_filter == "all":
        suite.addTests(loader.loadTestsFromTestCase(test_tier4_scenarios.TestTier4RealWorldScenarios))

    return suite


def main():
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. E2E Test Suite Runner")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "all"], default="all", help="Target test tier")
    parser.add_argument("--milestone", choices=["M1", "M2", "M3", "M4", "M5", "M6", "all"], default="all", help="Target milestone")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose test execution logs")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--failfast", action="store_true", help="Stop on first failure or error")
    args = parser.parse_args()

    suite = build_suite(tier_filter=args.tier, milestone_filter=args.milestone)
    result = StructuredTestResult(verbose=args.verbose)

    if not args.json:
        print("=" * 70)
        print(" J.A.R.V.I.S. UNIFIED E2E TEST RUNNER")
        print(f" Target Tier: {args.tier} | Target Milestone: {args.milestone}")
        print("=" * 70)

    start_time = time.time()
    suite.run(result)
    duration = time.time() - start_time

    total_tests = result.testsRun
    passed_count = len(result.successes)
    failed_count = len(result.failures)
    error_count = len(result.errors)
    skipped_count = len(result.skipped)

    summary_data = {
        "total_tests": total_tests,
        "passed": passed_count,
        "failed": failed_count,
        "errors": error_count,
        "skipped": skipped_count,
        "duration_sec": round(duration, 3),
        "tier_stats": result.tier_stats,
        "milestone_stats": result.milestone_stats,
        "status": "PASSED" if (failed_count == 0 and error_count == 0) else "FAILED",
    }

    if args.json:
        print(json.dumps(summary_data, indent=2))
    else:
        print("\n" + "-" * 70)
        print(f" Execution completed in {duration:.3f}s")
        print(f" Total Tests Run : {total_tests}")
        print(f" Passed           : {passed_count}")
        print(f" Skipped (Pending): {skipped_count}")
        print(f" Failed           : {failed_count}")
        print(f" Errors           : {error_count}")
        print("-" * 70)

        print("\n[ Tier Breakdown ]")
        for tier_name, stats in result.tier_stats.items():
            if sum(stats.values()) > 0:
                print(f"  * {tier_name:<28}: Passed={stats['passed']}, Skipped={stats['skipped']}, Failed={stats['failed']}, Errors={stats['error']}")

        print("\n[ Milestone Breakdown ]")
        for m_name, stats in result.milestone_stats.items():
            if sum(stats.values()) > 0:
                print(f"  * {m_name:<10}: Passed={stats['passed']}, Skipped={stats['skipped']}, Failed={stats['failed']}, Errors={stats['error']}")

        print("=" * 70)
        if summary_data["status"] == "PASSED":
            print(f" RESULT: SUCCESS (All active requirements satisfied)")
        else:
            print(f" RESULT: FAILURE ({failed_count} failures, {error_count} errors)")
        print("=" * 70)

    if failed_count > 0 or error_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
