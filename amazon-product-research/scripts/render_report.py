#!/usr/bin/env python3
"""
Render a Markdown product research report from analysis JSON + products JSON.

Usage:
    python render_report.py --products products_estimated.json --analysis analysis.json --keyword "silicone spatula" --out report.md
"""
from __future__ import annotations
import argparse
import json
from datetime import date
from pathlib import Path


def bar(score: float, max_score: float = 10, width: int = 10) -> str:
    filled = round(score / max_score * width)
    return "█" * filled + "░" * (width - filled)


def render(products: list[dict], analysis: dict, keyword: str) -> str:
    today = date.today().isoformat()
    comp = analysis.get("competition_score", 0)
    opp = analysis.get("opportunity_score", 0)
    revenue = analysis.get("market_monthly_revenue_usd", 0)
    avg_price = analysis.get("average_price_usd", 0)
    avg_reviews = analysis.get("average_reviews", 0)
    signals = analysis.get("signals", [])
    red_flags = analysis.get("red_flags", [])

    if opp >= 7 and comp <= 5:
        verdict = "GO — Strong opportunity with manageable competition"
    elif opp >= 6 and comp <= 6:
        verdict = "CONDITIONAL GO — Opportunity exists but requires differentiation"
    elif opp >= 5 and comp <= 4:
        verdict = "CONDITIONAL GO — Low competition but moderate market size"
    else:
        verdict = "NO-GO — High competition or insufficient market size"

    lines = [
        f"# Amazon Product Research: {keyword}",
        f"",
        f"> Generated: {today} | Products analyzed: {analysis.get('products_analyzed', len(products))}",
        f"",
        f"---",
        f"",
        f"## Executive Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Competition Score | {comp}/10  {bar(comp)} |",
        f"| Opportunity Score | {opp}/10  {bar(opp)} |",
        f"| Est. Market Revenue | ${revenue:,}/month |",
        f"| Average Price | ${avg_price:.2f} |",
        f"| Average Reviews | {int(avg_reviews):,} |",
        f"| FBA Dominance | {analysis.get('fba_dominance_ratio', 0)*100:.0f}% |",
        f"",
        f"**Verdict: {verdict}**",
        f"",
        f"---",
        f"",
        f"## Opportunity Signals",
        f"",
    ]

    for s in signals or ["No significant positive signals detected"]:
        lines.append(f"- {s}")

    lines += ["", "## Red Flags", ""]
    for r in red_flags or ["No significant red flags detected"]:
        lines.append(f"- {r}")

    lines += [
        f"",
        f"---",
        f"",
        f"## Top Products",
        f"",
        f"| # | ASIN | Title | Price | Rating | Reviews | Est. Sales/mo | BSR |",
        f"|---|------|-------|-------|--------|---------|---------------|-----|",
    ]

    for i, p in enumerate(products[:20], 1):
        title = (p.get("title") or "")[:50]
        lines.append(
            f"| {i} | {p.get('asin','')} | {title} | "
            f"${p.get('price') or 0:.2f} | {p.get('rating') or 0:.1f} | "
            f"{p.get('review_count') or 0:,} | {p.get('estimated_monthly_sales') or 0:,} | "
            f"{p.get('bsr') or '-'} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## Methodology",
        f"",
        f"- **Data source:** Amazon.com live scrape via Playwright (no paid API)",
        f"- **Sales estimation:** BSR power-law model — `base_rate × BSR^-0.55`, calibrated per category",
        f"- **Competition scoring:** Weighted composite of avg reviews, rating, brand concentration, FBA ratio, Amazon presence",
        f"- **Opportunity scoring:** Market revenue, review evenness, price point, rating gap, competition penalty",
        f"",
        f"*Snapshot data — prices, ranks, and review counts change daily.*",
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Markdown research report")
    parser.add_argument("--products", required=True, help="Products JSON with estimated_monthly_sales")
    parser.add_argument("--analysis", required=True, help="Analysis JSON from analyze_products.py")
    parser.add_argument("--keyword", required=True, help="Research keyword")
    parser.add_argument("--out", required=True, help="Output Markdown file path")
    args = parser.parse_args()

    products = json.loads(Path(args.products).read_text(encoding="utf-8"))
    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    report = render(products, analysis, args.keyword)
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"Report written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
