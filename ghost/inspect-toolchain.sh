#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "============================================================"
echo " LINUM GHOST BOOTSTRAP — TOOLCHAIN INVENTORY"
echo "============================================================"

printf '\n%-12s %s\n' "COMPILER" "PATH"

for c in qcc clang gcc cc zig rustc cargo ld as objcopy objdump; do
    if command -v "$c" >/dev/null 2>&1; then
        path="$(command -v "$c")"
        printf '%-12s %s\n' "$c" "$path"
        "$c" --version 2>&1 | head -1 || true
    else
        printf '%-12s %s\n' "$c" "NOT FOUND"
    fi
done

echo
echo "LINUM Rust workspace:"
cargo metadata --no-deps --format-version 1 2>/dev/null |
    python3 -c '
import json,sys
x=json.load(sys.stdin)
for p in x["packages"]:
    print(f"  {p["name"]}")
' 2>/dev/null || true
