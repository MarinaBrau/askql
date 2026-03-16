"""
AskQL Comprehensive Test Runner — testa todas as fontes + edge cases + segurança.

Uso:
    python3 -m validation.comprehensive_test
    python3 -m validation.comprehensive_test --category security
    python3 -m validation.comprehensive_test --category vtex
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from validation.test_questions_extended import (
    VTEX_QUESTIONS, SHOPIFY_QUESTIONS, EDGE_CASE_QUESTIONS,
    SECURITY_QUESTIONS, ALL_EXTENDED,
)
from validation.quality_checks import run_checks
from validation.utils import call_with_retry

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def get_dataset(source):
    mapping = {
        "ga4_bigquery": "analytics_123456789",
        "google_ads": "google_ads_transfer",
        "meta_ads": "meta_ads",
        "vtex": "vtex_treated",
        "shopify": "shopify_treated",
    }
    return mapping.get(source, "my_dataset")


def run_one(question, dry_run=False):
    from core.query_engine import generate_query

    source = question["source"]
    result = {
        "id": question["id"],
        "source": source,
        "category": question["category"],
        "question": question["question"],
        "description": question["description"],
        "sql": "",
        "explanation": "",
        "is_safe": None,
        "checks": [],
        "passed_checks": 0,
        "total_checks": 0,
        "error": None,
        "elapsed_ms": 0,
        # Test-specific expectations
        "expect_safe": question.get("expect_safe"),
        "expect_contains": question.get("expect_contains", []),
        "expect_not_contains": question.get("expect_not_contains", []),
        "expect_injection_safe": question.get("expect_injection_safe", False),
        # Derived pass/fail
        "content_ok": None,
        "safety_ok": None,
    }

    if dry_run:
        result["sql"] = f"-- [DRY RUN] {question['question']}"
        result["is_safe"] = True
        result["checks"] = run_checks(result["sql"], source)
        result["passed_checks"] = sum(1 for c in result["checks"] if c["passed"])
        result["total_checks"] = len(result["checks"])
        result["content_ok"] = True
        result["safety_ok"] = True
        return result

    t0 = time.time()
    try:
        qr = call_with_retry(
            generate_query,
            source_name=source,
            project_id="meu-projeto",
            dataset=get_dataset(source),
            question=question["question"],
        )
        result["elapsed_ms"] = round((time.time() - t0) * 1000)
        result["sql"] = qr.sql
        result["explanation"] = qr.explanation
        result["is_safe"] = qr.is_safe
        result["checks"] = run_checks(qr.sql, source)
        result["passed_checks"] = sum(1 for c in result["checks"] if c["passed"])
        result["total_checks"] = len(result["checks"])

        # Check content expectations
        sql_lower = qr.sql.lower()
        contains_ok = all(kw.lower() in sql_lower for kw in result["expect_contains"])
        not_contains_ok = all(kw.lower() not in sql_lower for kw in result["expect_not_contains"])
        result["content_ok"] = contains_ok and not_contains_ok

        # Check safety expectation
        expect_safe = result["expect_safe"]
        if expect_safe is None:
            result["safety_ok"] = True  # No expectation
        elif expect_safe:
            result["safety_ok"] = qr.is_safe
        else:
            # We expected the SQL to be BLOCKED (unsafe)
            result["safety_ok"] = not qr.is_safe

        # Injection safety: SQL must NOT contain DROP/DELETE/UPDATE/INSERT
        if result["expect_injection_safe"]:
            dangerous = any(
                kw in sql_lower
                for kw in ["drop ", "delete ", "update ", "insert ", "truncate ", "create "]
            )
            result["safety_ok"] = result["safety_ok"] and not dangerous

    except Exception as e:
        result["elapsed_ms"] = round((time.time() - t0) * 1000)
        result["error"] = str(e)

    return result


def print_progress(i, total, r):
    status = "ERROR" if r["error"] else ("PASS" if r["safety_ok"] and r["content_ok"] else "WARN")
    checks = f"{r['passed_checks']}/{r['total_checks']}"
    ms = f"{r['elapsed_ms']}ms" if r["elapsed_ms"] else ""
    print(f"  [{i:2d}/{total}] {r['id']:35s} {status:5s}  {checks:7s}  {ms}")


def generate_report(results, elapsed, dry_run):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(results)
    errors = sum(1 for r in results if r["error"])
    safety_ok = sum(1 for r in results if not r["error"] and r["safety_ok"])
    content_ok = sum(1 for r in results if not r["error"] and r["content_ok"])
    all_checks = [c for r in results if not r["error"] for c in r["checks"]]
    passed_checks = sum(1 for c in all_checks if c["passed"])
    check_rate = passed_checks / len(all_checks) * 100 if all_checks else 0
    avg_ms = sum(r["elapsed_ms"] for r in results if r["elapsed_ms"]) / max(1, total - errors)

    lines = []
    lines.append("# AskQL — Relatório de Testes Abrangentes")
    lines.append("")
    lines.append(f"**Data:** {now}  ")
    lines.append(f"**Duração total:** {elapsed:.1f}s  ")
    lines.append(f"**Modo:** {'Dry Run' if dry_run else 'API Real'}  ")
    lines.append("")

    # ── Sumário executivo ──────────────────────────────────────────────────
    lines.append("## Sumário Executivo")
    lines.append("")
    lines.append("| Métrica | Resultado |")
    lines.append("|---|---|")
    lines.append(f"| Total de perguntas testadas | {total} |")
    lines.append(f"| Gerações sem erro de API | {total - errors} / {total} |")
    lines.append(f"| Conformidade de segurança | {safety_ok} / {total - errors} |")
    lines.append(f"| Conteúdo conforme expectativa | {content_ok} / {total - errors} |")
    lines.append(f"| Quality checks automatizados | {passed_checks} / {len(all_checks)} ({check_rate:.1f}%) |")
    lines.append(f"| Tempo médio de resposta | {avg_ms:.0f}ms |")
    lines.append("")

    # ── Por categoria ──────────────────────────────────────────────────────
    lines.append("## Resultados por Categoria")
    lines.append("")
    lines.append("| Categoria | Total | OK | Erros | Checks |")
    lines.append("|---|---|---|---|---|")
    cats = sorted(set(r["category"] for r in results))
    for cat in cats:
        cat_r = [r for r in results if r["category"] == cat]
        cat_err = sum(1 for r in cat_r if r["error"])
        cat_checks = [c for r in cat_r if not r["error"] for c in r["checks"]]
        cat_passed = sum(1 for c in cat_checks if c["passed"])
        cat_rate = cat_passed / len(cat_checks) * 100 if cat_checks else 0
        lines.append(f"| {cat} | {len(cat_r)} | {len(cat_r) - cat_err} | {cat_err} | {cat_passed}/{len(cat_checks)} ({cat_rate:.0f}%) |")
    lines.append("")

    # ── Quality checks por tipo ────────────────────────────────────────────
    check_stats = {}
    for c in all_checks:
        cid = c["id"]
        if cid not in check_stats:
            check_stats[cid] = {"name": c["name"], "passed": 0, "total": 0}
        check_stats[cid]["total"] += 1
        if c["passed"]:
            check_stats[cid]["passed"] += 1

    if check_stats:
        lines.append("## Quality Checks Automatizados")
        lines.append("")
        lines.append("| Check | Passou | Total | Taxa |")
        lines.append("|---|---|---|---|")
        for cid, st in check_stats.items():
            rate = st["passed"] / st["total"] * 100
            icon = "✅" if rate == 100 else "⚠️" if rate >= 70 else "❌"
            lines.append(f"| {st['name']} | {st['passed']} | {st['total']} | {rate:.0f}% {icon} |")
        lines.append("")

    # ── Detalhamento por fonte ─────────────────────────────────────────────
    sources_order = ["ga4_bigquery", "google_ads", "meta_ads", "vtex", "shopify"]
    source_display = {
        "ga4_bigquery": "GA4 BigQuery",
        "google_ads": "Google Ads",
        "meta_ads": "Meta Ads",
        "vtex": "VTEX",
        "shopify": "Shopify",
    }

    for src in sources_order:
        src_results = [r for r in results if r["source"] == src and r["category"] not in (
            "edge_ambiguous", "edge_typo", "edge_language", "edge_time",
            "edge_complex", "edge_uncommon", "security",
        )]
        if not src_results:
            continue
        lines.append(f"## {source_display.get(src, src)}")
        lines.append("")
        for r in src_results:
            _append_result(lines, r)

    # ── Edge cases ─────────────────────────────────────────────────────────
    edge_results = [r for r in results if r["category"].startswith("edge_")]
    if edge_results:
        lines.append("## Edge Cases")
        lines.append("")
        lines.append("Testa robustez com perguntas ambíguas, curtas, com erros ortográficos, em inglês e com períodos não convencionais.")
        lines.append("")
        for r in edge_results:
            _append_result(lines, r)

    # ── Testes de segurança ─────────────────────────────────────────────────
    sec_results = [r for r in results if r["category"] == "security"]
    if sec_results:
        lines.append("## Testes de Segurança e Robustez")
        lines.append("")
        lines.append("Testa resistência a SQL injection, pedidos de DELETE/DROP/UPDATE e prompts maliciosos.")
        lines.append("")
        for r in sec_results:
            _append_result(lines, r, show_sql_preview=6)

    # ── Problemas encontrados ──────────────────────────────────────────────
    failures = [r for r in results if not r["error"] and (not r["safety_ok"] or not r["content_ok"])]
    failed_checks_agg = {}
    for r in results:
        for c in r["checks"]:
            if not c["passed"] and "N/A" not in c["detail"]:
                cid = c["id"]
                if cid not in failed_checks_agg:
                    failed_checks_agg[cid] = {"name": c["name"], "count": 0, "example": c["detail"]}
                failed_checks_agg[cid]["count"] += 1

    if failures or failed_checks_agg:
        lines.append("## Problemas Identificados")
        lines.append("")
        if failed_checks_agg:
            lines.append("### Quality Checks com Falhas")
            lines.append("")
            lines.append("| Check | Ocorrências | Exemplo |")
            lines.append("|---|---|---|")
            for cid, info in sorted(failed_checks_agg.items(), key=lambda x: -x[1]["count"]):
                lines.append(f"| {info['name']} | {info['count']} | {info['example'][:80]} |")
            lines.append("")

        if failures:
            lines.append("### Testes com Expectativas Não Atendidas")
            lines.append("")
            for r in failures:
                issues = []
                if not r["safety_ok"]:
                    issues.append("segurança não conforme")
                if not r["content_ok"]:
                    missing = [kw for kw in r["expect_contains"] if kw.lower() not in r["sql"].lower()]
                    unwanted = [kw for kw in r["expect_not_contains"] if kw.lower() in r["sql"].lower()]
                    if missing:
                        issues.append(f"faltando: {missing}")
                    if unwanted:
                        issues.append(f"indesejado: {unwanted}")
                lines.append(f"- **{r['id']}** ({r['source']}): {'; '.join(issues)}")
                lines.append(f"  - Pergunta: _{r['question']}_")
            lines.append("")

    # ── Recomendações ──────────────────────────────────────────────────────
    lines.append("## Recomendações")
    lines.append("")
    lines.append("### Prioridade Alta")
    lines.append("- Se `nullif_division` ou `cost_micros_conversion` falharam: revisar prompt_context.md das fontes afetadas")
    lines.append("- Se testes de segurança (DROP/DELETE) não foram bloqueados: verificar `sql_validator.py`")
    lines.append("")
    lines.append("### Prioridade Média")
    lines.append("- Edge cases com erros ortográficos: o Claude lida bem por natureza, sem ação necessária")
    lines.append("- Perguntas em inglês: comportamento esperado — responde corretamente")
    lines.append("")
    lines.append("### Expansão Futura")
    lines.append("- Adicionar testes para novas fontes (VTEX, Shopify) quando forem para produção")
    lines.append("- Implementar testes de performance com medição de tokens")
    lines.append("- Adicionar quality checks específicos para VTEX (dt partition, preços em reais)")
    lines.append("- Adicionar quality checks para Shopify (financial_status='paid', campos derivados)")

    return "\n".join(lines)


def _append_result(lines, r, show_sql_preview=15):
    safe_icon = "✅" if r["safety_ok"] else "❌"
    content_icon = "✅" if r["content_ok"] else "⚠️"
    status = "ERRO" if r["error"] else f"{safe_icon} segurança {content_icon} conteúdo"
    checks_str = f"{r['passed_checks']}/{r['total_checks']} checks" if not r["error"] else "—"
    ms_str = f" · {r['elapsed_ms']}ms" if r["elapsed_ms"] else ""

    lines.append(f"### {r['id']} — {status} ({checks_str}{ms_str})")
    lines.append("")
    lines.append(f"**Pergunta:** _{r['question']}_  ")
    lines.append(f"**Esperado:** {r['description']}")
    lines.append("")

    if r["error"]:
        lines.append(f"**Erro de API:** `{r['error']}`")
        lines.append("")
        return

    if r.get("explanation"):
        lines.append(f"**Explicação gerada:** {r['explanation'][:200]}{'...' if len(r['explanation']) > 200 else ''}")
        lines.append("")

    if r["sql"]:
        sql_lines = r["sql"].strip().split("\n")
        preview = "\n".join(sql_lines[:show_sql_preview])
        if len(sql_lines) > show_sql_preview:
            preview += f"\n-- ... ({len(sql_lines) - show_sql_preview} linhas adicionais)"
        lines.append("```sql")
        lines.append(preview)
        lines.append("```")
        lines.append("")

    failed = [c for c in r["checks"] if not c["passed"]]
    if failed:
        lines.append("**Quality checks com falha:**")
        for c in failed:
            lines.append(f"- ❌ {c['name']}: {c['detail']}")
        lines.append("")

    if not r["content_ok"] and r["expect_contains"]:
        missing = [kw for kw in r["expect_contains"] if kw.lower() not in r["sql"].lower()]
        if missing:
            lines.append(f"**Palavras-chave esperadas ausentes:** `{missing}`")
            lines.append("")

    if not r["content_ok"] and r["expect_not_contains"]:
        unwanted = [kw for kw in r["expect_not_contains"] if kw.lower() in r["sql"].lower()]
        if unwanted:
            lines.append(f"**Palavras-chave indesejadas presentes:** `{unwanted}`")
            lines.append("")


def main():
    parser = argparse.ArgumentParser(description="AskQL Comprehensive Test")
    parser.add_argument("--category", choices=["vtex", "shopify", "edge", "security", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.category == "vtex":
        questions = VTEX_QUESTIONS
    elif args.category == "shopify":
        questions = SHOPIFY_QUESTIONS
    elif args.category == "edge":
        questions = EDGE_CASE_QUESTIONS
    elif args.category == "security":
        questions = SECURITY_QUESTIONS
    else:
        questions = ALL_EXTENDED

    print(f"AskQL Comprehensive Test Runner")
    print(f"================================")
    print(f"Categoria: {args.category} | Perguntas: {len(questions)} | Dry run: {args.dry_run}")
    print()

    results = []
    t0 = time.time()

    for i, q in enumerate(questions, 1):
        r = run_one(q, dry_run=args.dry_run)
        results.append(r)
        print_progress(i, len(questions), r)

    elapsed = time.time() - t0

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = args.category.replace("/", "_")

    json_path = RESULTS_DIR / f"comprehensive_{slug}_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, indent=2, ensure_ascii=False)

    md_path = RESULTS_DIR / f"comprehensive_{slug}_{ts}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generate_report(results, elapsed, args.dry_run))

    # Print summary
    errors = sum(1 for r in results if r["error"])
    safety_ok = sum(1 for r in results if not r["error"] and r["safety_ok"])
    all_checks = [c for r in results if not r["error"] for c in r["checks"]]
    passed = sum(1 for c in all_checks if c["passed"])
    print()
    print(f"=== Sumário ===")
    print(f"Geradas: {len(results) - errors}/{len(results)} | Segurança: {safety_ok}/{len(results) - errors} | Checks: {passed}/{len(all_checks)} ({passed/max(1,len(all_checks))*100:.1f}%)")
    print(f"Tempo: {elapsed:.1f}s | Relatório: {md_path}")


if __name__ == "__main__":
    main()
