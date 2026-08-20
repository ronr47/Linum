#!/usr/bin/env bash
set -euo pipefail

echo "[*] Patching fix_hardcore_theme_and_tests.sh..."
sed -i 's/^print("\[+\] Industrial CLI theme generated\.")/echo "[+] Industrial CLI theme generated."/' fix_hardcore_theme_and_tests.sh

echo "[*] Patching fix_verifier_and_deploy_nala_fx.sh..."
sed -i 's/^print("✔ Deployed Nala\/Pixi-grade live progress matrix into CLI\.")/echo "✔ Deployed Nala\/Pixi-grade live progress matrix into CLI."/' fix_verifier_and_deploy_nala_fx.sh

echo "[*] Validating syntax with bash -n..."
bash -n fix_hardcore_theme_and_tests.sh
bash -n fix_verifier_and_deploy_nala_fx.sh

echo "[✓] Both scripts passed syntax validation."
