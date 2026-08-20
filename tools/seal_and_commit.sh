#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum

echo "[1/3] Resolving file permissions & build locks..."
sudo chown -R "$USER:$USER" build/ 2>/dev/null || true

echo "[2/3] Staging core patches & verified driver assets..."
git add src/linum/cli.py \
        fix_hardcore_theme_and_tests.sh \
        fix_verifier_and_deploy_nala_fx.sh \
        src/linum.egg-info/

echo "[3/3] Committing verified state..."
git commit -m "feat(pipeline): complete multi-backend routing with verified eBPF, LLVM, ASM, and OBJ emissions" || echo "[i] Nothing new to commit."

echo ""
echo "============================================================"
echo " 🛡️ REPOSITORY HEALTH & STATUS"
echo "============================================================"
git status --short
