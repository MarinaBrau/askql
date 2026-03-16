"""
AskQL Validation CLI — runs test questions through the query engine and produces quality reports.

Usage:
    python -m validation.validate                        # All 22 questions
    python -m validation.validate --source ga4_bigquery  # GA4 only (14)
    python -m validation.validate --source google_ads    # Google Ads only (8)
    python -m validation.validate --dry-run              # Framework test without API calls
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from validation.test_questions import get_questions, get_sources
from validation.quality_checks import run_checks
from validation.utils import call_with_retry


RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Default test config
DEFAULT_PROJECT_ID = "meu-projeto"
DEFAULT_GA4_DATASET = "analytics_123456789"
DEFAULT_GADS_DATASET = "google_ads_transfer"


def get_dataset_for_source(source):
    """Return default dataset for a given source."""
    if source == "ga4_bigquery":
        return DEFAULT_GA4_DATASET
    elif source == "google_ads":
        return DEFAULT_GADS_DATASET
    return "my_dataset"


def run_single_question(question, dry_run=False):
    """
    Run a single test question through the query engine.

    Returns dict with: question_id, source, question, sql, explanation,
    is_safe, checks, passed_checks, total_checks, error
    """
    source = question["source"]
    dataset = get_dataset_for_source(source)
    secondary_source = question.get("secondary_source")
    secondary_dataset = question.get("secondary_dataset")
    is_cross_source = secondary_source is not None

    result = {
        "question_id": question["id"],
        "source": source,
        "category": question["category"],
        "question": question["question"],
        "description": question["description"],
        "sql": "",
        "explanation": "",
        "is_safe": False,
        "checks": [],
        "passed_checks": 0,
        "total_checks": 0,
        "error": None,
    }

    if dry_run:
        result["sql"] = f"-- [DRY RUN] SQL would be generated for: {question['question']}"
        result["explanation"] = "[DRY RUN] No API call made"
        result["is_safe"] = True
        result["checks"] = run_checks(result["sql"], source, is_cross_source=is_cross_source)
        result["passed_checks"] = sum(1 for c in result["checks"] if c["passed"])
        result["total_checks"] = len(result["checks"])
        return result

    try:
        from core.query_engine import generate_query

        qr = call_with_retry(
            generate_query,
            source_name=source,
            project_id=DEFAULT_PROJECT_ID,
            dataset=dataset,
            question=question["question"],
            secondary_source=secondary_source,
            secondary_dataset=secondary_dataset,
        )
        result["sql"] = qr.sql
        result["explanation"] = qr.explanation
        result["is_safe"] = qr.is_safe

        # Run quality checks on generated SQL
        result["checks"] = run_checks(qr.sql, source, is_cross_source=is_cross_source)
        result["passed_checks"] = sum(1 for c in result["checks"] if c["passed"])
        result["total_checks"] = len(result["checks"])

    except Exception as e:
        result["error"] = str(e)

    return result


def generate_markdown_report(results, elapsed_seconds):
    """Generate a human-readable Markdown report from validation results."""
    total = len(results)
    errors = sum(1 for r in results if r["error"])
    successful = total - errors

    # Calculate check stats
    all_checks = []
    for r in results:
        if not r["error"]:
            all_checks.extend(r["checks"])

    total_checks = len(all_checks)
    passed_checks = sum(1 for c in all_checks if c["passed"])
    check_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    lines = []
    lines.append("# AskQL Validation Report")
    lines.append("")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Duration:** {elapsed_seconds:.1f}s")
    lines.append(f"**Questions:** {total} ({successful} successful, {errors} errors)")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Total questions | {total} |")
    lines.append(f"| Successful generations | {successful} |")
    lines.append(f"| API errors | {errors} |")
    lines.append(f"| Total quality checks | {total_checks} |")
    lines.append(f"| Passed checks | {passed_checks} |")
    lines.append(f"| **Check pass rate** | **{check_rate:.1f}%** |")
    lines.append("")

    # Check pass rate by check type
    check_stats = {}
    for c in all_checks:
        cid = c["id"]
        if cid not in check_stats:
            check_stats[cid] = {"name": c["name"], "passed": 0, "total": 0}
        check_stats[cid]["total"] += 1
        if c["passed"]:
            check_stats[cid]["passed"] += 1

    if check_stats:
        lines.append("## Check Pass Rate by Type")
        lines.append("")
        lines.append("| Check | Passed | Total | Rate |")
        lines.append("|---|---|---|---|")
        for cid, stats in check_stats.items():
            rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            icon = "PASS" if rate == 100 else "FAIL" if rate < 50 else "WARN"
            lines.append(f"| {stats['name']} | {stats['passed']} | {stats['total']} | {rate:.0f}% {icon} |")
        lines.append("")

    # Per-source breakdown
    for source in sorted(set(r["source"] for r in results)):
        source_results = [r for r in results if r["source"] == source]
        lines.append(f"## {source}")
        lines.append("")

        for r in source_results:
            status = "ERROR" if r["error"] else "OK"
            checks_summary = f"{r['passed_checks']}/{r['total_checks']} checks"
            lines.append(f"### {r['question_id']} — {status} ({checks_summary})")
            lines.append("")
            lines.append(f"**Question:** {r['question']}")
            lines.append(f"**Expected:** {r['description']}")
            lines.append("")

            if r["error"]:
                lines.append(f"**Error:** `{r['error']}`")
                lines.append("")
                continue

            # Show SQL preview (first 20 lines)
            if r["sql"]:
                sql_lines = r["sql"].strip().split("\n")
                preview = "\n".join(sql_lines[:20])
                if len(sql_lines) > 20:
                    preview += f"\n-- ... ({len(sql_lines) - 20} more lines)"
                lines.append("```sql")
                lines.append(preview)
                lines.append("```")
                lines.append("")

            # Show check results
            failed = [c for c in r["checks"] if not c["passed"]]
            if failed:
                lines.append("**Failed checks:**")
                for c in failed:
                    lines.append(f"- {c['name']}: {c['detail']}")
                lines.append("")

    # Common issues
    common_issues = {}
    for r in results:
        for c in r["checks"]:
            if not c["passed"] and "N/A" not in c["detail"]:
                issue = c["id"]
                if issue not in common_issues:
                    common_issues[issue] = {"name": c["name"], "detail": c["detail"], "count": 0}
                common_issues[issue]["count"] += 1

    if common_issues:
        lines.append("## Common Issues")
        lines.append("")
        lines.append("| Issue | Count | Detail |")
        lines.append("|---|---|---|")
        for issue_id, info in sorted(common_issues.items(), key=lambda x: -x[1]["count"]):
            lines.append(f"| {info['name']} | {info['count']} | {info['detail']} |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AskQL SQL Generation Validator")
    parser.add_argument(
        "--source",
        choices=get_sources(),
        default=None,
        help="Filter by source (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test framework without calling Claude API",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(RESULTS_DIR),
        help="Directory for output files",
    )
    args = parser.parse_args()

    questions = get_questions(source=args.source)
    source_label = args.source or "all"

    print(f"AskQL Validation Runner")
    print(f"=======================")
    print(f"Source: {source_label}")
    print(f"Questions: {len(questions)}")
    print(f"Dry run: {args.dry_run}")
    print()

    results = []
    start_time = time.time()

    for i, q in enumerate(questions, 1):
        status_prefix = f"[{i}/{len(questions)}]"
        print(f"{status_prefix} {q['id']}: {q['question'][:60]}...", end=" ", flush=True)

        result = run_single_question(q, dry_run=args.dry_run)
        results.append(result)

        if result["error"]:
            print(f"ERROR: {result['error'][:50]}")
        else:
            checks_ok = result["passed_checks"]
            checks_total = result["total_checks"]
            print(f"OK ({checks_ok}/{checks_total} checks)")

    elapsed = time.time() - start_time

    # Generate reports
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON report
    json_path = output_dir / f"validation_{timestamp}.json"
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "source_filter": args.source,
        "dry_run": args.dry_run,
        "total_questions": len(questions),
        "elapsed_seconds": round(elapsed, 1),
        "results": results,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # Markdown report
    md_path = output_dir / f"validation_{timestamp}.md"
    md_report = generate_markdown_report(results, elapsed)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    # Print summary
    print()
    print(f"--- Summary ---")
    total_checks = sum(r["total_checks"] for r in results)
    passed_checks = sum(r["passed_checks"] for r in results)
    errors = sum(1 for r in results if r["error"])
    check_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    print(f"Questions: {len(questions)} ({len(questions) - errors} OK, {errors} errors)")
    print(f"Quality checks: {passed_checks}/{total_checks} passed ({check_rate:.1f}%)")
    print(f"Time: {elapsed:.1f}s")
    print(f"JSON: {json_path}")
    print(f"Report: {md_path}")


if __name__ == "__main__":
    main()
