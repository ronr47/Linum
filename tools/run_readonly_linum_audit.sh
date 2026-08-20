#!/usr/bin/env bash
set -uo pipefail

# ==============================================================================
# LINUM WORKSPACE READ-ONLY AUDIT & INTEGRITY CHECK
# ==============================================================================

AUDIT_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
AUDIT_REPORT="linum_audit_report_${AUDIT_TIMESTAMP//:/_}.md"

echo "=================================================================="
echo " Starting Linum Read-Only Workspace Audit"
echo " Timestamp: ${AUDIT_TIMESTAMP}"
echo " Output Report: ${AUDIT_REPORT}"
echo "=================================================================="

{
    echo "# Linum Workspace Audit Report"
    echo ""
    echo "- **Audit Timestamp:** \`${AUDIT_TIMESTAMP}\`"
    echo "- **Working Directory:** \`$(pwd)\`"
    echo "- **Git Branch:** \`$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'N/A')\`"
    echo "- **Head Commit:** \`$(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')\`"
    echo ""
    echo "---"
    echo ""
    
    echo "## 1. Git Repository State"
    echo ""
    echo '```text'
    git status --short 2>/dev/null || echo "Not a git repository or git error."
    echo '```'
    echo ""
    
    echo "## 2. Source Code vs Artifact Breakdown"
    echo ""
    
    RUST_FILES=$(find . -maxdepth 3 -type f -name "*.rs" 2>/dev/null | wc -l)
    PYTHON_FILES=$(find . -maxdepth 3 -type f -name "*.py" 2>/dev/null | wc -l)
    SHELL_FILES=$(find . -maxdepth 3 -type f -name "*.sh" 2>/dev/null | wc -l)
    LINUM_FILES=$(find . -maxdepth 3 -type f -name "*.linum" 2>/dev/null | wc -l)
    OBJECT_FILES=$(find . -maxdepth 3 -type f -name "*.o" 2>/dev/null | wc -l)
    LLVM_MLIR_FILES=$(find . -maxdepth 3 -type f \( -name "*.ll" -o -name "*.mlir" -o -name "*.smt2" \) 2>/dev/null | wc -l)
    
    echo "| File Category | Extension / Pattern | Count |"
    echo "| :--- | :--- | :--- |"
    echo "| Rust Sources | \`*.rs\` | ${RUST_FILES} |"
    echo "| Python Scripts | \`*.py\` | ${PYTHON_FILES} |"
    echo "| Shell Automations | \`*.sh\` | ${SHELL_FILES} |"
    echo "| Linum DSL Files | \`*.linum\` | ${LINUM_FILES} |"
    echo "| Compiled Object Artifacts | \`*.o\` | ${OBJECT_FILES} |"
    echo "| Intermediate / IR / Formal Specs | \`*.ll\`, \`*.mlir\`, \`*.smt2\` | ${LLVM_MLIR_FILES} |"
    echo ""
    
    echo "## 3. Shell Script Audit (Executable Permissions & Validation)"
    echo ""
    echo "| Script Name | Executable | Syntax Check (bash -n) |"
    echo "| :--- | :--- | :--- |"
    
    shopt -s nullglob
    for script in *.sh; do
        if [[ -f "${script}" ]]; then
            IS_EXEC="No"
            [[ -x "${script}" ]] && IS_EXEC="Yes"
            
            SYNTAX_STATUS="Valid"
            if ! bash -n "${script}" 2>/dev/null; then
                SYNTAX_STATUS="Syntax Error"
            fi
            
            echo "| \`${script}\` | ${IS_EXEC} \vert{}${SYNTAX_STATUS} |"
        fi
    done
    echo ""

    echo "## 4. Root Rust Artifacts & Source Mapping"
    echo ""
    echo "| Rust Source | Corresponding Binary Present |"
    echo "| :--- | :--- |"
    for rs_file in *.rs; do
        if [[ -f "${rs_file}" ]]; then
            bin_name="${rs_file%.rs}"
            BIN_EXISTS="No"
            [[ -f "${bin_name}" && -x "${bin_name}" ]] && BIN_EXISTS="Yes (\`${bin_name}\`)"
            echo "| \`${rs_file}\` | ${BIN_EXISTS} |"
        fi
    done
    echo ""

    echo "## 5. Verification & Formal Specification Assets"
    echo ""
    for spec in *.smt2 *.mlir *.ll; do
        if [[ -f "${spec}" ]]; then
            FILE_SIZE=$(stat -c%s "${spec}" 2>/dev/null \vert{}\vert{} wc -c < "${spec}")
            LINE_COUNT=$(wc -l < "${spec}")
            echo "- **\`${spec}\`**: ${LINE_COUNT} lines (${FILE_SIZE} bytes)"
        fi
    done
    echo ""

    echo "## 6. Checksum Integrity Summary"
    echo ""
    CHECKSUM_FILE=""
    if [[ -f "RELEASE_CHECKSUMS.sha256" ]]; then
        CHECKSUM_FILE="RELEASE_CHECKSUMS.sha256"
    elif [[ -f "CHECKSUMS.sha256" ]]; then
        CHECKSUM_FILE="CHECKSUMS.sha256"
    fi

    if [[ -n "${CHECKSUM_FILE}" ]]; then
        echo "Validating against \`${CHECKSUM_FILE}\` (Read-only):"
        echo '```text'
        sha256sum --check --ignore-missing "${CHECKSUM_FILE}" 2>/dev/null || echo "Checksum validation completed with missing/failed files."
        echo '```'
    else
        echo "_No checksum file (\`RELEASE_CHECKSUMS.sha256\` or \`CHECKSUMS.sha256\`) found in root directory._"
    fi
    shopt -u nullglob

} > "${AUDIT_REPORT}"

echo "[✓] Audit complete. Review report: ${AUDIT_REPORT}"
cat "${AUDIT_REPORT}"
