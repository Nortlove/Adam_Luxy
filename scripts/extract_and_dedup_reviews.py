"""
Extract reviews from additional_reviews_and_ads.md and Blacklane_Reviews_1000plus.xlsx,
deduplicate against existing 518 deep-annotated reviews, and prepare for annotation.
Also extracts advertising copy as seller-side data.
"""

import json
import re
import os
import pandas as pd
from difflib import SequenceMatcher

REVIEWS_DIR = os.path.join(os.path.dirname(__file__), "..", "reviews")


def similarity(a: str, b: str) -> float:
    """Quick similarity check using first 100 chars for speed, full text for borderline."""
    a_lower = a.lower().strip()[:200]
    b_lower = b.lower().strip()[:200]
    if a_lower == b_lower:
        return 1.0
    # Quick length check
    if abs(len(a) - len(b)) > max(len(a), len(b)) * 0.5:
        return 0.0
    return SequenceMatcher(None, a_lower, b_lower).ratio()


def extract_reviews_from_markdown(filepath: str) -> list:
    """Parse the markdown table format to extract individual reviews."""
    reviews = []
    current_company = None
    current_source = None

    with open(filepath, "r") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect company headers (## Company Name: ...)
        if line.startswith("## ") and not line.startswith("## Additional"):
            # Extract company name
            company_match = re.match(r"^## (.+?):", line)
            if company_match:
                current_company = company_match.group(1).strip()
                # Normalize some names
                name_map = {
                    "SIXT ride": "SIXT Ride",
                    "Carey International": "Carey",
                    "LUXY Ride": "LUXY Ride",
                    "Uber Black / Comfort / Lux and Lyft Lux / Black": "Uber/Lyft Premium",
                }
                for k, v in name_map.items():
                    if k in current_company:
                        current_company = v

        # Detect source context
        if "Trustpilot" in line and ("Source:" in line or "reviews" in line.lower()):
            current_source = "Trustpilot"
        elif "Yelp" in line and ("Source:" in line or "reviews" in line.lower()):
            current_source = "Yelp"
        elif "TripAdvisor" in line:
            current_source = "TripAdvisor"
        elif "Sitejabber" in line:
            current_source = "Sitejabber"
        elif "BBB" in line and "rating" in line.lower():
            current_source = "BBB"
        elif "Apple App Store" in line:
            current_source = "Apple App Store"
        elif "Google Play" in line:
            current_source = "Google Play"
        elif "Reddit" in line or "UberPeople" in line:
            current_source = "Reddit/Forum"
        elif "Travel Blog" in line or "One Mile" in line:
            current_source = "Travel Blog"

        # Parse table rows with review text
        if line.startswith("|") and '"' in line:
            # Extract quoted review text
            text_match = re.search(r'"(.+?)"', line)
            if text_match:
                review_text = text_match.group(1)
                # Skip very short texts
                if len(review_text) < 30:
                    i += 1
                    continue

                # Extract star rating
                rating = None
                star_match = re.search(r"★{1,5}", line)
                if star_match:
                    rating = len(star_match.group())
                # Also check for explicit star text
                if not rating:
                    rating_match = re.search(r"(\d)/5", line)
                    if rating_match:
                        rating = int(rating_match.group(1))

                # Extract reviewer name
                parts = line.split("|")
                reviewer = parts[1].strip() if len(parts) > 1 else "Anonymous"

                # Detect sentiment from context
                sentiment = None
                if "Negative" in line or "negative" in line:
                    sentiment = "negative"
                    if not rating:
                        rating = 2
                elif "Positive" in line or "positive" in line:
                    sentiment = "positive"
                    if not rating:
                        rating = 4

                if not rating:
                    rating = 3  # default neutral

                reviews.append({
                    "company": current_company or "Unknown",
                    "source": current_source or "Unknown",
                    "rating": rating,
                    "review_text": review_text,
                    "reviewer": reviewer,
                    "data_source": "additional_reviews_and_ads.md",
                })

        i += 1

    return reviews


def extract_ads_from_markdown(filepath: str) -> list:
    """Extract advertising copy as seller-side data."""
    ads = []
    current_company = None

    with open(filepath, "r") as f:
        content = f.read()

    # Split at CATEGORY 2: ADVERTISING LANGUAGE
    if "CATEGORY 2: ADVERTISING LANGUAGE" in content:
        ad_section = content.split("CATEGORY 2: ADVERTISING LANGUAGE")[1]
    else:
        return ads

    lines = ad_section.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Company headers
        if line.startswith("## ") and ":" in line:
            company_match = re.match(r"^## (.+?):", line)
            if company_match:
                current_company = company_match.group(1).strip()

        # Extract quoted copy with bold markers
        bold_quotes = re.findall(r'\*\*"(.+?)"\*\*', line)
        for q in bold_quotes:
            if len(q) > 15 and current_company:
                ads.append({
                    "company": current_company,
                    "copy_text": q,
                    "copy_type": "tagline" if len(q) < 60 else "description",
                })

        # Also get non-bold quoted text that looks like ad copy
        if current_company and line.startswith("-") and '"' in line:
            regular_quotes = re.findall(r'"(.+?)"', line)
            for q in regular_quotes:
                if len(q) > 20 and q not in [a["copy_text"] for a in ads]:
                    ads.append({
                        "company": current_company,
                        "copy_text": q,
                        "copy_type": "supporting_copy",
                    })

        i += 1

    return ads


def extract_excel_reviews(filepath: str) -> list:
    """Extract reviews from Blacklane Excel file."""
    df = pd.read_excel(filepath)
    reviews = []

    for _, row in df.iterrows():
        text = str(row.get("Review Text", "")).strip()
        if not text or text == "nan" or len(text) < 30:
            continue

        # Parse rating
        rating_str = str(row.get("Rating (Stars)", ""))
        rating_match = re.search(r"(\d)", rating_str)
        rating = int(rating_match.group(1)) if rating_match else 3

        reviews.append({
            "company": "Blacklane",
            "source": str(row.get("Source", "Trustpilot")),
            "rating": rating,
            "review_text": text,
            "reviewer": "Anonymous",
            "date": str(row.get("Date", "")),
            "data_source": "Blacklane_Reviews_1000plus.xlsx",
        })

    return reviews


def deduplicate(new_reviews: list, existing_texts: set, threshold: float = 0.85) -> list:
    """Remove reviews that are duplicates of existing ones."""
    unique = []
    seen_new = set()

    for r in new_reviews:
        text = r["review_text"]
        text_key = text.lower().strip()[:100]

        # Quick exact match on first 100 chars
        if text_key in existing_texts:
            continue
        if text_key in seen_new:
            continue

        # Check against existing with similarity
        is_dup = False
        for existing in existing_texts:
            if similarity(text, existing) > threshold:
                is_dup = True
                break

        if not is_dup:
            unique.append(r)
            seen_new.add(text_key)

    return unique


def main():
    # Load existing annotated review texts for dedup
    annotated_path = os.path.join(REVIEWS_DIR, "luxury_car_service_deep_annotated.json")
    with open(annotated_path) as f:
        annotated = json.load(f)

    existing_texts = set()
    for r in annotated["annotated_reviews"]:
        text = r.get("_text", "")
        if text:
            existing_texts.add(text.lower().strip()[:100])

    # Also load expanded reviews
    expanded_path = os.path.join(REVIEWS_DIR, "luxury_car_service_reviews_expanded.json")
    with open(expanded_path) as f:
        expanded = json.load(f)
    for r in expanded["reviews"]:
        text = r.get("text", "")
        if text:
            existing_texts.add(text.lower().strip()[:100])

    print(f"Existing review fingerprints: {len(existing_texts)}")

    # Extract from markdown
    md_path = os.path.join(REVIEWS_DIR, "additional_reviews_and_ads.md")
    md_reviews = extract_reviews_from_markdown(md_path)
    print(f"Extracted from markdown: {len(md_reviews)} reviews")

    # Extract ads
    md_ads = extract_ads_from_markdown(md_path)
    print(f"Extracted ad copy entries: {len(md_ads)}")

    # Extract from Excel
    excel_path = os.path.join(REVIEWS_DIR, "Blacklane_Reviews_1000plus.xlsx")
    excel_reviews = extract_excel_reviews(excel_path)
    print(f"Extracted from Excel: {len(excel_reviews)} reviews")

    # Combine all new reviews
    all_new = md_reviews + excel_reviews
    print(f"Total new reviews before dedup: {len(all_new)}")

    # Deduplicate
    unique_reviews = deduplicate(all_new, existing_texts)
    print(f"Unique new reviews after dedup: {len(unique_reviews)}")

    # Company breakdown
    from collections import Counter
    company_counts = Counter(r["company"] for r in unique_reviews)
    print("\nBy company:")
    for company, count in company_counts.most_common():
        print(f"  {company}: {count}")

    # Rating distribution
    rating_counts = Counter(r["rating"] for r in unique_reviews)
    print("\nBy rating:")
    for rating in sorted(rating_counts.keys()):
        print(f"  {rating} stars: {rating_counts[rating]}")

    # Save unique reviews for annotation
    output_path = os.path.join(REVIEWS_DIR, "new_reviews_for_annotation.json")
    with open(output_path, "w") as f:
        json.dump({
            "metadata": {
                "source_files": ["additional_reviews_and_ads.md", "Blacklane_Reviews_1000plus.xlsx"],
                "total_extracted": len(all_new),
                "duplicates_removed": len(all_new) - len(unique_reviews),
                "unique_count": len(unique_reviews),
            },
            "reviews": unique_reviews,
        }, f, indent=2)
    print(f"\nSaved {len(unique_reviews)} reviews to {output_path}")

    # Save ads
    ads_output = os.path.join(REVIEWS_DIR, "luxury_car_service_ads_expanded.json")
    with open(ads_output, "w") as f:
        json.dump({
            "metadata": {"source": "additional_reviews_and_ads.md", "count": len(md_ads)},
            "ads": md_ads,
        }, f, indent=2)
    print(f"Saved {len(md_ads)} ad copy entries to {ads_output}")


if __name__ == "__main__":
    main()
