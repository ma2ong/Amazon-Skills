---
name: amazon-product-research
description: Free Amazon product research — scrapes Amazon search results, product detail pages, and Best Sellers via Playwright, estimates monthly sales from BSR, and produces a scored opportunity report. No paid API required.
---

# Amazon Product Research (Free Edition)

Research Amazon product opportunities using live scraped data. No Sorftime MCP, no Jungle Scout subscription, no API keys needed.

**Data sources:**
- Amazon search results (Playwright)
- Amazon product detail pages (Playwright)
- Amazon Best Sellers pages (Playwright)
- Customer review pages (Playwright)
- Keepa product pages (Playwright screenshot for price history)
- BSR → sales estimation (local Python script, no API)

**Scripts location:** `C:\Users\Administrator\.claude\skills\amazon-product-research\scripts\`

---

## Step 1: Gather Input

Ask the user for:
1. **Keyword or product idea** (e.g. "silicone ice cube tray", "portable blender")
2. **Marketplace** (default: amazon.com; options: amazon.co.uk, amazon.de, amazon.co.jp, amazon.ca)
3. **Output directory** (default: `C:\Users\Administrator\Desktop\research\{keyword-slug}\`)

Create the output directory:
```
New-Item -ItemType Directory -Force -Path "{workdir}"
```

---

## Step 2: Scrape Amazon Search Results

Navigate to: `https://www.{marketplace}/s?k={url-encoded-keyword}`

On pages 1 and 2 (navigate to page 2 via `&page=2`), for each product card extract:
- `asin` — from `data-asin` attribute
- `title` — product title text
- `brand` — brand name if shown
- `price` — numeric USD price
- `rating` — star rating float (e.g. 4.3)
- `review_count` — integer
- `is_sponsored` — true if "Sponsored" label present
- `has_bestseller_badge` — true if "Best Seller" badge present
- `has_amazons_choice` — true if "Amazon's Choice" badge present
- `position` — 1-indexed position on page

Build a JSON array and save to: `{workdir}\search_raw.json`

**Notes:**
- Use `mcp__playwright__browser_navigate` then `mcp__playwright__browser_snapshot` to read the DOM
- Wait 2 seconds between page loads (`mcp__playwright__browser_wait_for`)
- If a CAPTCHA appears, stop and tell the user
- Skip sponsored listings for competition analysis; record them separately

---

## Step 3: Scrape Product Detail Pages

Take the top 15 non-sponsored ASINs from Step 2. For each, navigate to:
`https://www.{marketplace}/dp/{asin}`

Extract:
- `title` — full product title
- `brand` — from "Brand:" or byline
- `price` — current price (numeric)
- `list_price` — crossed-out "was" price if shown
- `rating` — star rating
- `review_count` — total reviews
- `bsr` — Best Seller Rank integer (from "Product Details" or sidebar)
- `bsr_category` — top-level category for BSR (e.g. "Home & Kitchen")
- `bsr_subcategory` — sub-category if a second rank is shown
- `date_first_available` — from Product Details table
- `seller_name` — "Sold by" text
- `is_amazon_sold` — true if sold by "Amazon.com"
- `is_fba` — true if "Fulfilled by Amazon" or "Ships from Amazon"
- `offer_count` — number of seller offers
- `has_aplus` — true if A+ content section is visible
- `variation_count` — number of size/color variations (count swatches)
- `images_count` — number of images in the gallery

Save to: `{workdir}\products_detail.json`

---

## Step 4: Scrape Amazon Best Sellers (recommended)

Find the Best Sellers URL for the primary category identified in Step 3.
Navigate to: `https://www.amazon.com/Best-Sellers/zgbs/{category-path}/`

Extract the top 20 entries:
- rank (1-20), asin, title, price, rating, review_count

Save to: `{workdir}\bestsellers.json`

---

## Step 5: Review Sentiment (top 5 products by review count)

For the 5 most-reviewed products, navigate to:
`https://www.amazon.com/product-reviews/{asin}?sortBy=recent&pageNumber=1`

Extract 10 reviews per page (get pages 1 and 2 = 20 reviews per product):
- star_rating, title, date, verified_purchase, body (first 300 chars)

From all reviews, identify:
- **Top 3 praised features** (keywords: "love", "perfect", "great", "works well", "easy")
- **Top 3 pain points** (keywords: "broke", "cheap", "disappointed", "returned", "waste", "doesn't work")
- **Improvement requests** (keywords: "wish", "should", "if only", "would be better")

Save raw reviews to: `{workdir}\reviews_raw.json`
Save summary to: `{workdir}\review_sentiment.json` as:
```json
{
  "praised_features": ["...", "...", "..."],
  "pain_points": ["...", "...", "..."],
  "improvement_requests": ["...", "..."]
}
```

---

## Step 6: Keepa Price History (top 3 products by estimated sales)

For the top 3 products, navigate to:
`https://keepa.com/#!product/1-{asin}` (region 1 = US; 2=UK, 3=DE, 9=CA)

Wait 6 seconds for chart render (`mcp__playwright__browser_wait_for`).

Take a screenshot: `mcp__playwright__browser_take_screenshot` → save to `{workdir}\keepa_{asin}.png`

If text price data is visible on page, extract: current price, 30-day low, 90-day low.
If chart is canvas-only, the screenshot is sufficient for visual inspection — note in report.

---

## Step 7: Run BSR Estimation

Merge `search_raw.json` and `products_detail.json` into one array (detail data takes priority for overlapping fields).
Save to: `{workdir}\products_merged.json`

Run:
```powershell
python "C:\Users\Administrator\.claude\skills\amazon-product-research\scripts\bsr_estimator.py" `
  --batch "{workdir}\products_merged.json" `
  --out "{workdir}\products_estimated.json"
```

---

## Step 8: Run Competition & Opportunity Analysis

```powershell
python "C:\Users\Administrator\.claude\skills\amazon-product-research\scripts\analyze_products.py" `
  --input "{workdir}\products_estimated.json" `
  --output "{workdir}\analysis.json"
```

---

## Step 9: Generate Report

```powershell
python "C:\Users\Administrator\.claude\skills\amazon-product-research\scripts\render_report.py" `
  --products "{workdir}\products_estimated.json" `
  --analysis "{workdir}\analysis.json" `
  --keyword "{keyword}" `
  --out "{workdir}\report.md"
```

Read `report.md` and display the full contents in the conversation.

---

## Step 10: Present Summary

After displaying the report, give the user a 5-point summary:

1. **Verdict** (GO / CONDITIONAL GO / NO-GO) with one-sentence reason
2. **Market size** and **average price**
3. **Top 2 opportunity signals**
4. **Top 2 red flags**
5. **Recommended next action** (e.g. "Order 10 samples and test a listing", "Pivot to sub-niche X", "Too competitive — consider adjacent category")

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Amazon CAPTCHA | Stop immediately, tell user to try later or use different network |
| 404 on product page | Skip that ASIN, continue with remaining |
| BSR not shown | Set `bsr: 0`, mark as "BSR unavailable" in report |
| Price shows as range (variants) | Use lowest visible price |
| Keepa won't load | Skip, note "Keepa unavailable" in report — continue |
| Review page returns 0 results | Skip that ASIN's review scrape |

---

## Marketplace Region Codes (for Keepa URLs)

| Marketplace | Domain | Keepa Region |
|-------------|--------|--------------|
| US | amazon.com | 1 |
| UK | amazon.co.uk | 2 |
| Germany | amazon.de | 3 |
| France | amazon.fr | 4 |
| Japan | amazon.co.jp | 5 |
| Canada | amazon.ca | 6 |
| China | amazon.cn | 7 |
| Italy | amazon.it | 8 |
| Spain | amazon.es | 9 |
| India | amazon.in | 10 |
