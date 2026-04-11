#!/usr/bin/env python3
"""
Political Enrichment by ZIP Code

Uses 2024 Presidential Election results at the county level to provide
granular political leaning data for each ZIP code.

Data sources:
- ZIP to County: github.com/scpike/us-state-county-zip
- 2024 Election Results: github.com/tonmcg/US_County_Level_Election_Results_08-24
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# =============================================================================
# DATA PATHS
# =============================================================================

POLITICAL_DATA_DIR = Path(__file__).parent.parent / "Political" / "county_data"
ZIP_COUNTY_FILE = POLITICAL_DATA_DIR / "zip_county_geo.csv"
COUNTY_ELECTION_FILE = POLITICAL_DATA_DIR / "2024_county_election.csv"


# =============================================================================
# POLITICAL LEAN CLASSIFICATION
# =============================================================================

def classify_political_lean(gop_pct: float, dem_pct: float) -> Dict[str, Any]:
    """
    Classify political leaning based on vote percentages.
    
    Returns detailed classification with:
    - lean_category: strong_republican, republican, lean_republican, swing, 
                     lean_democratic, democratic, strong_democratic
    - lean_score: -1.0 (most D) to +1.0 (most R)
    - margin: GOP % - Dem %
    - ideology_label: conservative, center-right, moderate, center-left, liberal, progressive
    """
    margin = gop_pct - dem_pct
    lean_score = margin  # Already in -1 to 1 range
    
    # Classify by margin
    if margin > 0.30:
        lean_category = "strong_republican"
        ideology = "conservative"
    elif margin > 0.15:
        lean_category = "republican"
        ideology = "conservative"
    elif margin > 0.05:
        lean_category = "lean_republican"
        ideology = "center-right"
    elif margin > -0.05:
        lean_category = "swing"
        ideology = "moderate"
    elif margin > -0.15:
        lean_category = "lean_democratic"
        ideology = "center-left"
    elif margin > -0.30:
        lean_category = "democratic"
        ideology = "liberal"
    else:
        lean_category = "strong_democratic"
        ideology = "progressive"
    
    return {
        "lean_category": lean_category,
        "lean_score": round(lean_score, 4),
        "margin": round(margin, 4),
        "gop_pct": round(gop_pct, 4),
        "dem_pct": round(dem_pct, 4),
        "ideology_label": ideology,
    }


# =============================================================================
# DATA LOADERS
# =============================================================================

class PoliticalEnrichment:
    """
    Provides ZIP code level political data enrichment.
    """
    
    def __init__(self):
        self.zip_to_county: Dict[str, Tuple[str, str]] = {}  # ZIP -> (county_name, state)
        self.county_to_political: Dict[str, Dict[str, Any]] = {}  # (county, state) -> political data
        self.state_political: Dict[str, Dict[str, Any]] = {}  # state -> aggregated political data
        self._loaded = False
    
    def load_data(self) -> bool:
        """Load all political data files."""
        if self._loaded:
            return True
        
        try:
            self._load_zip_county_mapping()
            self._load_county_election_data()
            self._aggregate_state_data()
            self._loaded = True
            logger.info(f"Political data loaded: {len(self.zip_to_county)} ZIPs, "
                       f"{len(self.county_to_political)} counties, "
                       f"{len(self.state_political)} states")
            return True
        except Exception as e:
            logger.error(f"Failed to load political data: {e}")
            return False
    
    def _load_zip_county_mapping(self):
        """Load ZIP code to county mapping."""
        if not ZIP_COUNTY_FILE.exists():
            raise FileNotFoundError(f"ZIP-county file not found: {ZIP_COUNTY_FILE}")
        
        with open(ZIP_COUNTY_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                zipcode = row.get("zipcode", "").strip()
                county = row.get("county", "").strip()
                state = row.get("state", "").strip()
                
                if zipcode and county and state:
                    # Store lowercase for matching
                    self.zip_to_county[zipcode] = (county.lower(), state.lower())
        
        logger.info(f"Loaded {len(self.zip_to_county)} ZIP-county mappings")
    
    def _load_county_election_data(self):
        """Load 2024 county election results."""
        if not COUNTY_ELECTION_FILE.exists():
            raise FileNotFoundError(f"Election file not found: {COUNTY_ELECTION_FILE}")
        
        with open(COUNTY_ELECTION_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                state_name = row.get("state_name", "").strip().lower()
                county_name = row.get("county_name", "").strip().lower()
                
                # Clean county name (remove " county" suffix)
                county_clean = county_name.replace(" county", "").replace(" parish", "").strip()
                
                try:
                    gop_pct = float(row.get("per_gop", 0))
                    dem_pct = float(row.get("per_dem", 0))
                    total_votes = int(float(row.get("total_votes", 0)))
                    
                    political = classify_political_lean(gop_pct, dem_pct)
                    political["total_votes"] = total_votes
                    political["county_name"] = county_name
                    political["state_name"] = state_name
                    political["county_fips"] = row.get("county_fips", "")
                    
                    # Store with multiple key formats for matching
                    key = (county_clean, state_name)
                    self.county_to_political[key] = political
                    
                    # Also store with full county name
                    key_full = (county_name, state_name)
                    self.county_to_political[key_full] = political
                    
                except (ValueError, TypeError) as e:
                    continue
        
        logger.info(f"Loaded election data for {len(self.county_to_political) // 2} counties")
    
    def _aggregate_state_data(self):
        """Aggregate county data to state level."""
        state_votes = {}  # state -> {gop_total, dem_total, total}
        
        # Track unique counties per state
        seen_counties = set()
        
        for (county, state), data in self.county_to_political.items():
            key = (county, state)
            if key in seen_counties:
                continue
            seen_counties.add(key)
            
            if state not in state_votes:
                state_votes[state] = {"gop": 0, "dem": 0, "total": 0, "counties": 0}
            
            # Use vote counts if available, otherwise estimate
            total = data.get("total_votes", 0)
            if total > 0:
                state_votes[state]["gop"] += total * data["gop_pct"]
                state_votes[state]["dem"] += total * data["dem_pct"]
                state_votes[state]["total"] += total
                state_votes[state]["counties"] += 1
        
        for state, votes in state_votes.items():
            if votes["total"] > 0:
                gop_pct = votes["gop"] / votes["total"]
                dem_pct = votes["dem"] / votes["total"]
                
                political = classify_political_lean(gop_pct, dem_pct)
                political["total_votes"] = int(votes["total"])
                political["counties_counted"] = votes["counties"]
                
                self.state_political[state] = political
    
    def get_political_by_zip(self, zipcode: str) -> Optional[Dict[str, Any]]:
        """
        Get political leaning data for a ZIP code.
        
        Returns None if ZIP not found.
        """
        if not self._loaded:
            self.load_data()
        
        zipcode = str(zipcode).strip()[:5]  # Ensure 5-digit ZIP
        
        if zipcode not in self.zip_to_county:
            return None
        
        county, state = self.zip_to_county[zipcode]
        
        # Try to find county data
        key = (county, state)
        if key in self.county_to_political:
            result = self.county_to_political[key].copy()
            result["source"] = "county"
            result["zipcode"] = zipcode
            return result
        
        # Fallback to state level
        if state in self.state_political:
            result = self.state_political[state].copy()
            result["source"] = "state_fallback"
            result["zipcode"] = zipcode
            result["note"] = f"County '{county}' not found, using state average"
            return result
        
        return None
    
    def get_political_by_county(self, county: str, state: str) -> Optional[Dict[str, Any]]:
        """Get political data for a county."""
        if not self._loaded:
            self.load_data()
        
        county_clean = county.lower().replace(" county", "").replace(" parish", "").strip()
        state_clean = state.lower().strip()
        
        key = (county_clean, state_clean)
        if key in self.county_to_political:
            return self.county_to_political[key].copy()
        
        return None
    
    def get_political_by_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Get aggregated political data for a state."""
        if not self._loaded:
            self.load_data()
        
        state_clean = state.lower().strip()
        return self.state_political.get(state_clean, {}).copy()
    
    def enrich_review(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add political context to a review based on business location.
        
        Looks for ZIP code in review's business_zip field or gmap_id lookup.
        """
        # Try to find ZIP code
        zipcode = review.get("business_zip") or review.get("postal_code") or review.get("zip_code")
        
        if not zipcode:
            return review
        
        political = self.get_political_by_zip(str(zipcode))
        
        if political:
            review["political_context"] = {
                "lean_category": political.get("lean_category"),
                "lean_score": political.get("lean_score"),
                "ideology_label": political.get("ideology_label"),
                "margin_2024": political.get("margin"),
                "source": political.get("source"),
            }
        
        return review
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded political data."""
        if not self._loaded:
            self.load_data()
        
        # Count by political lean
        lean_counts = {}
        for data in self.county_to_political.values():
            lean = data.get("lean_category", "unknown")
            lean_counts[lean] = lean_counts.get(lean, 0) + 1
        
        # Divide by 2 because we store each county twice
        lean_counts = {k: v // 2 for k, v in lean_counts.items()}
        
        return {
            "zip_codes_mapped": len(self.zip_to_county),
            "counties_with_data": len(self.county_to_political) // 2,
            "states_with_data": len(self.state_political),
            "counties_by_lean": lean_counts,
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_enrichment_instance: Optional[PoliticalEnrichment] = None


def get_political_enrichment() -> PoliticalEnrichment:
    """Get singleton instance of PoliticalEnrichment."""
    global _enrichment_instance
    if _enrichment_instance is None:
        _enrichment_instance = PoliticalEnrichment()
    return _enrichment_instance


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_political_by_zip(zipcode: str) -> Optional[Dict[str, Any]]:
    """Get political leaning for a ZIP code."""
    return get_political_enrichment().get_political_by_zip(zipcode)


def get_political_by_county(county: str, state: str) -> Optional[Dict[str, Any]]:
    """Get political leaning for a county."""
    return get_political_enrichment().get_political_by_county(county, state)


def enrich_review_with_politics(review: Dict[str, Any]) -> Dict[str, Any]:
    """Add political context to a review."""
    return get_political_enrichment().enrich_review(review)


# =============================================================================
# CLI TESTING
# =============================================================================

def main():
    """Test the political enrichment system."""
    enrichment = get_political_enrichment()
    enrichment.load_data()
    
    # Print stats
    stats = enrichment.get_stats()
    print("\n" + "=" * 60)
    print("POLITICAL ENRICHMENT STATISTICS")
    print("=" * 60)
    print(f"ZIP codes mapped:     {stats['zip_codes_mapped']:,}")
    print(f"Counties with data:   {stats['counties_with_data']:,}")
    print(f"States with data:     {stats['states_with_data']:,}")
    print("\nCounties by Political Lean:")
    for lean, count in sorted(stats["counties_by_lean"].items()):
        print(f"  {lean:20s}: {count:,}")
    
    # Test some ZIP codes
    test_zips = ["90210", "10001", "78701", "30301", "60601", "98101", "33101"]
    print("\n" + "=" * 60)
    print("TEST ZIP CODES")
    print("=" * 60)
    
    for zipcode in test_zips:
        political = get_political_by_zip(zipcode)
        if political:
            print(f"\nZIP {zipcode}:")
            print(f"  County:   {political.get('county_name', 'N/A')}, {political.get('state_name', 'N/A').title()}")
            print(f"  Lean:     {political.get('lean_category')} ({political.get('ideology_label')})")
            print(f"  GOP%:     {political.get('gop_pct', 0)*100:.1f}%")
            print(f"  Dem%:     {political.get('dem_pct', 0)*100:.1f}%")
            print(f"  Margin:   {political.get('margin', 0)*100:+.1f}%")
            print(f"  Score:    {political.get('lean_score', 0):+.4f}")
        else:
            print(f"\nZIP {zipcode}: Not found")
    
    # Test state aggregates
    print("\n" + "=" * 60)
    print("STATE AGGREGATES (Sample)")
    print("=" * 60)
    
    test_states = ["california", "texas", "florida", "new york", "pennsylvania"]
    for state in test_states:
        political = enrichment.get_political_by_state(state)
        if political:
            print(f"{state.title():15s}: {political.get('lean_category'):20s} "
                  f"(margin: {political.get('margin', 0)*100:+.1f}%)")


if __name__ == "__main__":
    main()
