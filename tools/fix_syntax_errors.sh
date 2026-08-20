#!/usr/bin/env bash
set -euo pipefail

echo "[*] Auditing syntax error details..."
for target in fix_hardcore_theme_and_tests.sh fix_verifier_and_deploy_nala_fx.sh; do
    if [[ -f "${target}" ]]; then
        echo "--------------------------------------------------"
        echo "File: ${target}"
        bash -n "${target}" || true
    fi
done
