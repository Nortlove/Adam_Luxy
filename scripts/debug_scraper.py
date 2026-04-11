#!/usr/bin/env python3
"""
Debug script to inspect page structure for review extraction.
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_amazon():
    """Debug Amazon page structure."""
    print("="*60)
    print("DEBUGGING AMAZON REVIEWS PAGE")
    print("="*60)
    
    # Use a product with lots of reviews
    asin = "B09V3KXJPB"  # Popular item
    reviews_url = f"https://www.amazon.com/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        print(f"Loading: {reviews_url}")
        response = await page.goto(reviews_url, wait_until="domcontentloaded", timeout=30000)
        print(f"Status: {response.status}")
        
        await asyncio.sleep(3)
        
        # Check for various review selectors
        selectors_to_try = [
            '[data-hook="review"]',
            '.review',
            '.a-section.review',
            '[data-hook="review-body"]',
            '.review-text',
            '.review-text-content',
            '[class*="review"]',
            'div[id*="review"]',
        ]
        
        print("\nTrying selectors:")
        for selector in selectors_to_try:
            elements = await page.query_selector_all(selector)
            print(f"  {selector}: {len(elements)} matches")
        
        # Get page title
        title = await page.title()
        print(f"\nPage title: {title}")
        
        # Check if we're blocked
        content = await page.content()
        if "robot" in content.lower() or "captcha" in content.lower():
            print("\n⚠️ POSSIBLE BOT DETECTION!")
        
        if "sign in" in content.lower() and len(content) < 50000:
            print("\n⚠️ POSSIBLE LOGIN REDIRECT!")
        
        # Save HTML for inspection
        html_path = "/Users/chrisnocera/Sites/adam-platform/scripts/debug_amazon.html"
        with open(html_path, "w") as f:
            f.write(content)
        print(f"\nSaved HTML to: {html_path}")
        print(f"HTML size: {len(content)} bytes")
        
        await browser.close()


async def debug_walmart():
    """Debug Walmart page structure."""
    print("\n" + "="*60)
    print("DEBUGGING WALMART PAGE")
    print("="*60)
    
    url = "https://www.walmart.com/ip/Instant-Pot-Duo-7-in-1-Electric-Pressure-Cooker-6-Qt-5-95-Liters/55025457"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        
        print(f"Loading: {url}")
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        print(f"Status: {response.status}")
        
        await asyncio.sleep(3)
        
        # Scroll to load reviews
        for i in range(5):
            await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {(i+1)/6})")
            await asyncio.sleep(0.5)
        
        # Check for review selectors
        selectors_to_try = [
            '[data-testid="review-card"]',
            '[data-testid="reviews"]',
            '.review-card',
            '[class*="review"]',
            '[class*="Review"]',
            'div[data-testid*="review"]',
        ]
        
        print("\nTrying selectors:")
        for selector in selectors_to_try:
            elements = await page.query_selector_all(selector)
            print(f"  {selector}: {len(elements)} matches")
        
        content = await page.content()
        html_path = "/Users/chrisnocera/Sites/adam-platform/scripts/debug_walmart.html"
        with open(html_path, "w") as f:
            f.write(content)
        print(f"\nSaved HTML to: {html_path}")
        print(f"HTML size: {len(content)} bytes")
        
        await browser.close()


async def main():
    await debug_amazon()
    await debug_walmart()


if __name__ == "__main__":
    asyncio.run(main())
