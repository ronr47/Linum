#!/data/data/com.termux/files/usr/bin/bash
set -u

ROOT="$HOME/linum"
EFI="${1:-$HOME/toolkit/firmware_uefi/BOOTX64.EFI}"
REPORT="$ROOT/reports/efi-audit.txt"
VALIDATOR="$ROOT/scripts/validate_pe32plus.py"

cd "$ROOT" || exit 1

if [ ! -f "$EFI" ]; then
    printf 'ERROR: EFI file not found: %s\n' "$EFI" >&2
    exit 1
fi

mkdir -p reports

run_check() {
    local label="$1"
    shift

    printf '\n=== %s ===\n' "$label"
    "$@"
    local status=$?

    printf 'EXIT_STATUS=%s\n' "$status"
    return "$status"
}

overall=0

{
    printf 'LINUM EFI STRUCTURAL AUDIT\n'
    printf 'Date: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf 'Target: %s\n' "$EFI"
    printf 'SHA256: '
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$EFI"
    else
        printf 'sha256sum unavailable\n'
    fi

    printf '\n=== FILE TYPE ===\n'
    if command -v file >/dev/null 2>&1; then
        file "$EFI" || overall=1
    else
        printf 'file utility unavailable\n'
    fi

    printf '\n=== PE STRUCTURAL VALIDATION ===\n'
    if [ -f "$VALIDATOR" ]; then
        python3 "$VALIDATOR" "$EFI" || overall=1
    else
        printf 'ERROR: Validator missing: %s\n' "$VALIDATOR"
        overall=1
    fi

    printf '\n=== INDEPENDENT LLVM HEADER CHECK ===\n'
    if command -v llvm-readobj >/dev/null 2>&1; then
        llvm-readobj --file-headers --sections "$EFI" || overall=1
    else
        printf 'llvm-readobj unavailable; skipped\n'
    fi

    printf '\n=== CODE DISASSEMBLY ===\n'
    if command -v llvm-objdump >/dev/null 2>&1; then
        llvm-objdump --disassemble --section=.text "$EFI" || overall=1
    else
        printf 'llvm-objdump unavailable; skipped\n'
    fi

    printf '\n=== PYTHON REGRESSION TESTS ===\n'
    python3 -m unittest discover -s tests -v || overall=1

    printf '\n=== AUDIT SUMMARY ===\n'
    if [ "$overall" -eq 0 ]; then
        printf 'AUDIT_COMMANDS=PASS\n'
    else
        printf 'AUDIT_COMMANDS=FAIL\n'
    fi

    printf 'NOTE: Structural checks do not establish runtime safety,\n'
    printf 'firmware compatibility, signature validity, or boot success.\n'
} > "$REPORT" 2>&1

cat "$REPORT"

printf '\nReport saved to: %s\n' "$REPORT"
exit "$overall"
