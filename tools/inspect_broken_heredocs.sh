#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "Inspecting fix_hardcore_theme_and_tests.sh (lines 175-200):"
echo "=================================================="
sed -n '175,200p' fix_hardcore_theme_and_tests.sh || true

echo ""
echo "=================================================="
echo "Inspecting fix_verifier_and_deploy_nala_fx.sh (lines 170-195):"
echo "=================================================="
sed -n '170,195p' fix_verifier_and_deploy_nala_fx.sh || true
