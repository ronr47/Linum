#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

FLIGHT_TARGET="${1:-W8519}"
API_CREDENTIAL="${2:-your_aviationstack_key_here}"

echo "============================================================"
echo " 1. COMPILING NATIVE TRAVEL INGESTION ENGINE"
echo "============================================================"
rm -f travel_spot_exec

if gcc -O3 -Wall -Wextra fetch_spot.c -o travel_spot_exec; then
    echo "✅ Native binary optimized and linked successfully."
else
    echo "❌ GCC Compilation hit a boundary fault."
    exit 1
fi

echo "============================================================"
echo " 2. FIRING RETRIEVAL PIPELINE"
echo "============================================================"
./travel_spot_exec "$FLIGHT_TARGET" "$API_CREDENTIAL"
