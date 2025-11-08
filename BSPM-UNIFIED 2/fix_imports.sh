#!/bin/bash
# fix_imports.sh - Fix import statements in backend Python files

set -e  # Exit on any error

echo "Fixing Python imports in backend directory..."
echo "=============================================="

# Navigate to project root
cd ~/BSPM-UNIFIED

# Backup backend directory first
echo "Creating backup..."
cp -r backend backend_backup_$(date +%Y%m%d_%H%M%S)

# Find all .py files in backend/ and fix imports
echo "Fixing imports..."
find backend -name "*.py" -type f -exec sed -i '' 's/from backend\./from /g' {} +

echo ""
echo "Verifying changes..."
echo "Files modified:"
grep -r "^from " backend/*.py backend/*/*.py 2>/dev/null | head -20

echo ""
echo "Done! Imports fixed."
echo ""
echo "Next: Rebuild Docker container"
