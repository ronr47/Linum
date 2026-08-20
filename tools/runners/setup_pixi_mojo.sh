#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " 📦 INITIALIZING PIXI & MODULAR ENVIRONMENT"
echo "============================================================"

if ! command -v pixi >/dev/null 2>&1; then
    echo "[*] Downloading and installing standalone Pixi..."
    curl -fsSL https://pixi.sh/install.sh | bash
    export PATH="${HOME}/.pixi/bin:${PATH}"
fi

echo "  [✔] Pixi Version: $(pixi --version)"

# Initialize local pixi workspace for Modular Mojo
cd /home/ron/linum
if [ ! -f "pixi.toml" ]; then
    pixi init --format toml . || true
    pixi add --channel conda-forge --channel https://conda.modular.com/max mojo || true
fi

echo "============================================================"
echo " [✔] Pixi Mojo Environment Configured."
echo "============================================================"
