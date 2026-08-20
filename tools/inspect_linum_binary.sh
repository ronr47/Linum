#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "1. Locating 'linum' command resolution:"
echo "=================================================="
which linum || true
type -a linum || true

echo ""
echo "=================================================="
echo "2. Searching for the fallback string across repo:"
echo "=================================================="
grep -rn "Unrecognized source extension" . || true

echo ""
echo "=================================================="
echo "3. Checking entry_points in pyproject.toml / setup.py:"
echo "=================================================="
grep -n -C 5 "linum =" pyproject.toml setup.py 2>/dev/null || true
