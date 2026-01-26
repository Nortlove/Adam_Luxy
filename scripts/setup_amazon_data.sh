#!/bin/bash
# =============================================================================
# ADAM Amazon Data Setup Script
# =============================================================================
#
# This script helps set up the Amazon review data for ADAM learning.
#
# The Amazon Review Dataset can be downloaded from:
# https://nijianmo.github.io/amazon/index.html
#
# Required files:
#   /amazon/
#   ├── All_Beauty.jsonl
#   ├── Amazon_Fashion.jsonl
#   ├── Beauty_and_Personal_Care.jsonl
#   ├── Books.jsonl
#   ├── Clothing_Shoes_and_Jewelry.jsonl
#   ├── Digital_Music.jsonl
#   ├── Grocery_and_Gourmet_Food.jsonl
#   ├── Kindle_Store.jsonl
#   ├── Magazine_Subscriptions.jsonl
#   ├── Movies_and_TV.jsonl
#   ├── meta_All_Beauty.jsonl
#   ├── meta_Amazon_Fashion.jsonl
#   └── ... (metadata files)
#
# =============================================================================

set -e

AMAZON_DATA_DIR="${1:-/amazon}"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                    ADAM Amazon Data Setup                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if directory exists
if [ -d "$AMAZON_DATA_DIR" ]; then
    echo "✓ Data directory exists: $AMAZON_DATA_DIR"
    
    # Count JSONL files
    JSONL_COUNT=$(ls -1 "$AMAZON_DATA_DIR"/*.jsonl 2>/dev/null | wc -l)
    echo "✓ Found $JSONL_COUNT JSONL files"
    
    # List categories
    echo ""
    echo "Available categories:"
    for f in "$AMAZON_DATA_DIR"/*.jsonl; do
        if [[ ! $(basename "$f") =~ ^meta_ ]]; then
            category=$(basename "$f" .jsonl)
            size=$(du -h "$f" | cut -f1)
            echo "  - $category ($size)"
        fi
    done
    
    echo ""
    echo "Ready to run ADAM learning!"
    echo ""
    echo "Commands:"
    echo "  # Quick test (5000 reviews per category)"
    echo "  python scripts/run_adam_learning.py --quick"
    echo ""
    echo "  # Full learning"
    echo "  python scripts/run_adam_learning.py"
    echo ""
    echo "  # Specific categories"
    echo "  python scripts/run_adam_learning.py --categories Books,Digital_Music"
    
else
    echo "✗ Data directory not found: $AMAZON_DATA_DIR"
    echo ""
    echo "To set up Amazon data:"
    echo ""
    echo "1. Download the Amazon Review Dataset (2018):"
    echo "   https://nijianmo.github.io/amazon/index.html"
    echo ""
    echo "2. Download these category files (5-core reviews):"
    echo "   - All_Beauty"
    echo "   - Amazon_Fashion"
    echo "   - Beauty_and_Personal_Care"
    echo "   - Books"
    echo "   - Clothing_Shoes_and_Jewelry"
    echo "   - Digital_Music"
    echo "   - Grocery_and_Gourmet_Food"
    echo "   - Kindle_Store"
    echo "   - Magazine_Subscriptions"
    echo "   - Movies_and_TV"
    echo ""
    echo "3. Create the data directory:"
    echo "   sudo mkdir -p $AMAZON_DATA_DIR"
    echo "   sudo chown \$USER $AMAZON_DATA_DIR"
    echo ""
    echo "4. Extract JSONL files to $AMAZON_DATA_DIR"
    echo ""
    echo "5. Run ADAM learning:"
    echo "   python scripts/run_adam_learning.py"
    echo ""
    
    # Offer to create a symlink if data is elsewhere
    echo "If your data is in a different location, you can create a symlink:"
    echo "   sudo ln -s /path/to/your/amazon/data $AMAZON_DATA_DIR"
fi

echo ""
