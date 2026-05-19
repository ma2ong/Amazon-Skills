#!/usr/bin/env python3
"""
BSR -> estimated monthly sales.

Usage:
    python bsr_estimator.py --bsr 342 --category "Home & Kitchen"
    python bsr_estimator.py --batch products.json --out estimates.json
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

BENCHMARKS_PATH = Path(__file__).parent.parent / "references" / "category_benchmarks.json"


def load_benchmarks() -> dict:
    return json.loads(BENCHMARKS_PATH.read_text(encoding="utf-8"))


def estimate_monthly_sales(bsr: int, category: str, benchmarks: dict | None = None) -> int:
    if benchmarks is None:
        benchmarks = load_benchmarks()
    cats = benchmarks["categories"]
    base = cats.get(category) or cats.get("default")
    exp = benchmarks.get("decay_exponent", 0.55)
    if bsr <= 0:
        return 0
    raw = base * math.pow(bsr, -exp)
    return max(0, round(raw))


def classify_velocity(monthly_sales: int) -> str:
    if monthly_sales >= 1000:
        return "high"
    if monthly_sales >= 300:
        return "medium"
    if monthly_sales >= 50:
        return "low"
    return "very_low"


def process_single(bsr: int, category: str) -> dict:
    benchmarks = load_benchmarks()
    sales = estimate_monthly_sales(bsr, category, benchmarks)
    return {
        "bsr": bsr,
        "category": category,
        "estimated_monthly_sales": sales,
        "velocity": classify_velocity(sales),
    }


def process_batch(products: list[dict]) -> list[dict]:
    benchmarks = load_benchmarks()
    results = []
    for p in products:
        bsr = p.get("bsr") or p.get("best_seller_rank") or 0
        cat = p.get("bsr_category") or p.get("category") or "default"
        sales = estimate_monthly_sales(int(bsr), cat, benchmarks)
        results.append({**p, "estimated_monthly_sales": sales, "velocity": classify_velocity(sales)})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate Amazon monthly sales from BSR")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bsr", type=int, help="Single BSR value")
    group.add_argument("--batch", type=str, help="Path to JSON array of products")
    parser.add_argument("--category", type=str, default="default", help="Amazon top-level category")
    parser.add_argument("--out", type=str, help="Output JSON path (batch mode)")
    args = parser.parse_args()

    if args.bsr is not None:
        result = process_single(args.bsr, args.category)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        products = json.loads(Path(args.batch).read_text(encoding="utf-8"))
        results = process_batch(products)
        out_path = args.out or args.batch.replace(".json", "_estimated.json")
        Path(out_path).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Processed {len(results)} products -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
