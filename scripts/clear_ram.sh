#!/bin/bash
# RAM Clearing Helper for ADAM Pipeline
# Run with: sudo ./scripts/clear_ram.sh

echo "=== Before Clearing ==="
vm_stat | grep -E "free|inactive|speculative"
sysctl vm.swapusage

echo ""
echo "Running purge..."
purge

sleep 2

echo ""
echo "=== After Clearing ==="
vm_stat | grep -E "free|inactive|speculative"
sysctl vm.swapusage

echo ""
echo "Done! Run this periodically to help the pipeline."
