#!/usr/bin/env bash
set -uo pipefail

BASE_DIR="$HOME/linum/canonical_workspace"
ENGINE="$BASE_DIR/tools/blackbox_core/blackbox_engine"
REPORT_DIR="$BASE_DIR/ir/json_reports"

# Explicitly configure the corpus location when necessary.
SXS_POOL="${SXS_POOL:-}"

if [[ -z "$SXS_POOL" ]]; then
    for candidate in \
        "$HOME/artifacts" \
        "$HOME/Downloads" \
        "$HOME/downloads" \
        "$HOME/storage/shared"
    do
        if [[ -d "$candidate" ]]; then
            count=$(find "$candidate" -type f \
                \( -iname '*.dll' -o -iname '*.sys' \
                   -o -iname '*.exe' -o -iname '*.winmd' \) \
                -print -quit 2>/dev/null)

            if [[ -n "$count" ]]; then
                SXS_POOL="$candidate"
                break
            fi
        fi
    done
fi

if [[ -z "$SXS_POOL" || ! -d "$SXS_POOL" ]]; then
    echo "ERROR: No configured corpus directory exists." >&2
    echo 'Set SXS_POOL to the actual corpus directory.' >&2
    exit 2
fi

if [[ ! -x "$ENGINE" ]]; then
    echo "ERROR: Engine missing or not executable: $ENGINE" >&2
    exit 3
fi

mkdir -p "$REPORT_DIR"

STAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$REPORT_DIR/atlas_manifest_$STAMP.csv"

printf '%s\n' 'path,status,exit_code' > "$REPORT"

TOTAL=0
VALID=0
REJECTED=0

echo "[*] Architecture: $(uname -m)"
echo "[*] Corpus: $SXS_POOL"
echo "[*] Manifest: $REPORT"

while IFS= read -r -d '' target; do
    TOTAL=$((TOTAL + 1))

    printf '[%s] %s\n' "$TOTAL" "$target"

    "$ENGINE" "$target"
    status=$?

    # CSV-escape embedded quotes in filenames.
    escaped=${target//\"/\"\"}

    if [[ "$status" -eq 66 ]]; then
        VALID=$((VALID + 1))
        printf '"%s",accepted,%d\n' "$escaped" "$status" >> "$REPORT"
    else
        REJECTED=$((REJECTED + 1))
        printf '"%s",rejected,%d\n' "$escaped" "$status" >> "$REPORT"
    fi
done < <(
    find "$SXS_POOL" -type f \
        \( -iname '*.dll' -o -iname '*.sys' \
           -o -iname '*.exe' -o -iname '*.winmd' \) \
        -print0 2>/dev/null
)

printf '\n=== ATLAS SUMMARY ===\n'
printf 'Corpus: %s\n' "$SXS_POOL"
printf 'Total: %d | Accepted: %d | Rejected: %d\n' \
    "$TOTAL" "$VALID" "$REJECTED"
printf 'Manifest: %s\n' "$REPORT"

if [[ "$TOTAL" -eq 0 ]]; then
    echo "WARNING: No matching binaries were found."
    exit 4
fi
