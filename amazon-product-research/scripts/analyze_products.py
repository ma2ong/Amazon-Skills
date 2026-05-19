#!/usr/bin/env python3
"""
Score competition intensity and opportunity viability for a scraped Amazon product set.

Input: JSON array of products (with estimated_monthly_sales added by bsr_estimator.py)
Output: JSON analysis object with competition_score, opportunity_score, signals, red_flags
"""
from __future__ import annotations
import argparse
import json
import statistics
from pathlib import Path


def _safe_mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def score_competition(products: list[dict]) -> float:
    """Return competition score 1-10 (higher = more competitive)."""
    if not products:
        return 5.0
    scores = []

    avg_reviews = _safe_mean([p.get("review_count") or 0 for p in products])
    if avg_reviews >= 5000:
        scores.append(9)
    elif avg_reviews >= 2000:
        scores.append(8)
    elif avg_reviews >= 1000:
        scores.append(7)
    elif avg_reviews >= 500:
        scores.append(6)
    elif avg_reviews >= 200:
        scores.append(5)
    elif avg_reviews >= 50:
        scores.append(3)
    else:
        scores.append(2)

    avg_rating = _safe_mean([p.get("rating") or 0 for p in products[:10]])
    if avg_rating >= 4.5:
        scores.append(8)
    elif avg_rating >= 4.2:
        scores.append(6)
    elif avg_rating >= 3.8:
        scores.append(4)
    else:
        scores.append(2)

    brands = [p.get("brand") or "" for p in products[:10] if p.get("brand")]
    unique_brands = len(set(b.lower() for b in brands)) if brands else len(products[:10])
    if unique_brands <= 2:
        scores.append(9)
    elif unique_brands <= 4:
        scores.append(7)
    elif unique_brands <= 7:
        scores.append(5)
    else:
        scores.append(3)

    fba_count = sum(1 for p in products if p.get("is_fba"))
    fba_ratio = fba_count / len(products) if products else 0
    scores.append(round(fba_ratio * 10))

    amazon_count = sum(1 for p in products if p.get("is_amazon_sold"))
    if amazon_count >= 3:
        scores.append(9)
    elif amazon_count >= 1:
        scores.append(7)
    else:
        scores.append(3)

    return round(min(10.0, max(1.0, _safe_mean(scores))), 1)


def score_opportunity(products: list[dict], competition_score: float) -> float:
    """Return opportunity score 1-10 (higher = better opportunity)."""
    if not products:
        return 3.0
    scores = []

    total_revenue = sum(
        (p.get("estimated_monthly_sales") or 0) * (p.get("price") or 0)
        for p in products
    )
    if total_revenue >= 500_000:
        scores.append(9)
    elif total_revenue >= 200_000:
        scores.append(8)
    elif total_revenue >= 80_000:
        scores.append(6)
    elif total_revenue >= 30_000:
        scores.append(5)
    else:
        scores.append(2)

    sorted_by_reviews = sorted(products, key=lambda p: p.get("review_count") or 0, reverse=True)
    top_reviews = sorted_by_reviews[0].get("review_count") or 1
    p10_reviews = sorted_by_reviews[min(9, len(sorted_by_reviews) - 1)].get("review_count") or 1
    gap_ratio = top_reviews / max(p10_reviews, 1)
    if gap_ratio >= 50:
        scores.append(2)
    elif gap_ratio >= 20:
        scores.append(4)
    elif gap_ratio >= 5:
        scores.append(7)
    else:
        scores.append(9)

    avg_price = _safe_mean([p.get("price") or 0 for p in products])
    if 20 <= avg_price <= 80:
        scores.append(8)
    elif 10 <= avg_price < 20 or 80 < avg_price <= 150:
        scores.append(6)
    elif avg_price > 150:
        scores.append(4)
    else:
        scores.append(2)

    avg_rating = _safe_mean([p.get("rating") or 0 for p in products])
    if avg_rating < 3.8:
        scores.append(8)
    elif avg_rating < 4.2:
        scores.append(6)
    else:
        scores.append(4)

    competition_penalty = (competition_score - 5) * 0.5
    raw = _safe_mean(scores) - competition_penalty
    return round(min(10.0, max(1.0, raw)), 1)


def generate_signals(products: list[dict], competition_score: float) -> tuple[list[str], list[str]]:
    signals = []
    red_flags = []

    avg_rating = _safe_mean([p.get("rating") or 0 for p in products])
    avg_reviews = _safe_mean([p.get("review_count") or 0 for p in products])
    avg_price = _safe_mean([p.get("price") or 0 for p in products])
    amazon_count = sum(1 for p in products if p.get("is_amazon_sold"))

    if avg_rating < 4.0:
        signals.append(f"Average rating {avg_rating:.1f} — customers not fully satisfied, product improvement opportunity")
    if avg_reviews < 200:
        signals.append("Low average review count — market not yet saturated, easier to rank")
    if avg_price >= 30:
        signals.append(f"Average price ${avg_price:.0f} — healthy FBA margin potential")
    if competition_score <= 4:
        signals.append("Low competition score — good window for new entrants")
    if avg_rating >= 4.5 and avg_reviews < 100:
        signals.append("High rating with low review count — early market, first-mover advantage possible")

    if amazon_count >= 2:
        red_flags.append(f"Amazon sells {amazon_count} products in this search — very hard to win buy box")
    if avg_reviews >= 2000:
        red_flags.append(f"Average {avg_reviews:.0f} reviews — significant social proof gap for new listings")
    if avg_price < 12:
        red_flags.append(f"Average price ${avg_price:.1f} — FBA fees likely exceed 40% of revenue")
    if competition_score >= 8:
        red_flags.append("Very high competition — consider sub-niche or major differentiation")

    return signals, red_flags


def analyze(products: list[dict]) -> dict:
    if not products:
        return {"error": "No products provided"}

    competition = score_competition(products)
    opportunity = score_opportunity(products, competition)
    signals, red_flags = generate_signals(products, competition)

    prices = [p.get("price") or 0 for p in products]
    total_revenue = sum(
        (p.get("estimated_monthly_sales") or 0) * (p.get("price") or 0)
        for p in products
    )
    avg_reviews = _safe_mean([p.get("review_count") or 0 for p in products])
    fba_count = sum(1 for p in products if p.get("is_fba"))

    if avg_reviews >= 1000:
        review_concentration = "high"
    elif avg_reviews >= 300:
        review_concentration = "medium"
    else:
        review_concentration = "low"

    return {
        "competition_score": competition,
        "opportunity_score": opportunity,
        "market_monthly_revenue_usd": round(total_revenue),
        "average_price_usd": round(_safe_mean(prices), 2),
        "average_reviews": round(avg_reviews),
        "review_concentration": review_concentration,
        "fba_dominance_ratio": round(fba_count / len(products), 2) if products else 0,
        "signals": signals,
        "red_flags": red_flags,
        "products_analyzed": len(products),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Amazon product opportunity")
    parser.add_argument("--input", "-i", required=True, help="JSON array of products with estimated_monthly_sales")
    parser.add_argument("--output", "-o", required=True, help="Output analysis JSON")
    args = parser.parse_args()

    products = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = analyze(products)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"competition={result['competition_score']} opportunity={result['opportunity_score']} revenue=${result['market_monthly_revenue_usd']:,}/mo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
