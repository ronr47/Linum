#!/usr/bin/env bash
set -euo pipefail

echo "[1/3] Fixing build directory permissions..."
sudo chown -R "$USER:$USER" build/xdp_prog/ 2>/dev/null || chmod -R u+rwX build/xdp_prog/ 2>/dev/null || true

echo "[2/3] Staging core fixes..."
git add fix_hardcore_theme_and_tests.sh \
        fix_verifier_and_deploy_nala_fx.sh \
        src/linum.egg-info/

echo "[3/3] Creating commit..."
git commit -m "fix(core): resolve shell heredoc syntax errors and sync compiler routing"

echo ""
echo "[✓] State successfully committed."
git status --short
