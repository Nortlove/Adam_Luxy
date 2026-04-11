#!/usr/bin/env python3
"""
Test script for Enterprise Review Scraper

Tests each implemented scraper against real product URLs.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adam.intelligence.scrapers.enterprise_scraper import (
    EnterpriseReviewScraper,
    get_enterprise_scraper,
)


# Test product URLs from each retailer - using popular products with many reviews
TEST_PRODUCTS = {
    # Amazon - Sony headphones with 50k+ reviews
    "amazon.com": "https://www.amazon.com/dp/B0BX2L8PWZ",
    # Walmart - highly reviewed item
    "walmart.com": "https://www.walmart.com/ip/Instant-Pot-Duo-7-in-1-Electric-Pressure-Cooker-6-Qt-5-95-Liters/55025457",
    # Target - popular item
    "target.com": "https://www.target.com/p/keurig-k-mini-single-serve-k-cup-pod-coffee-maker/-/A-53788559",
    # BestBuy - popular headphones
    "bestbuy.com": "https://www.bestbuy.com/site/apple-airpods-4-white/6572960.p",
    # Home Depot - popular drill
    "homedepot.com": "https://www.homedepot.com/p/DEWALT-20V-MAX-Cordless-Drill-Impact-Driver-2-Tool-Combo-Kit-with-2-1-3Ah-Batteries-Charger-and-Bag-DCK240C2/203300730",
}


async def test_single_scraper(scraper: EnterpriseReviewScraper, domain: str, url: str):
    """Test a single scraper."""
    print(f"\n{'='*60}")
    print(f"Testing: {domain}")
    print(f"URL: {url[:60]}...")
    print(f"{'='*60}")
    
    try:
        result = await scraper.scrape_product(url, max_reviews=20)  # Limit to 20 for testing
        
        print(f"Success: {result.success}")
        print(f"Reviews found: {len(result.reviews)}")
        print(f"Total found: {result.total_found}")
        print(f"Duration: {result.scrape_duration_ms:.0f}ms")
        
        if result.error_message:
            print(f"Error: {result.error_message}")
        
        if result.product_name:
            print(f"Product: {result.product_name[:50]}...")
        
        if result.reviews:
            print(f"\nSample review (first one):")
            review = result.reviews[0]
            print(f"  Rating: {review.rating}")
            print(f"  Verified: {review.verified_purchase}")
            print(f"  Text: {review.review_text[:150]}...")
        
        return result.success, len(result.reviews)
        
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False, 0


async def main():
    print("="*60)
    print("ENTERPRISE SCRAPER TEST")
    print("="*60)
    
    # Check if Playwright is available
    try:
        from playwright.async_api import async_playwright
        print("✓ Playwright is installed")
    except ImportError:
        print("✗ Playwright not installed!")
        print("  Run: pip install playwright && playwright install chromium")
        return
    
    scraper = get_enterprise_scraper(headless=True)
    
    results = {}
    
    for domain, url in TEST_PRODUCTS.items():
        success, count = await test_single_scraper(scraper, domain, url)
        results[domain] = {"success": success, "reviews": count}
    
    await scraper.close()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for domain, result in results.items():
        status = "✓" if result["success"] else "✗"
        print(f"{status} {domain}: {result['reviews']} reviews")
    
    total_success = sum(1 for r in results.values() if r["success"])
    print(f"\nTotal: {total_success}/{len(results)} scrapers succeeded")


if __name__ == "__main__":
    asyncio.run(main())
