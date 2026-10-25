#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$HOME/linum/canonical_workspace"
ENGINE="${BASE_DIR}/tools/blackbox_core/blackbox_engine"
IR_DIR="${BASE_DIR}/ir/json_reports"

if [[ ! -x "${ENGINE}" ]]; then
    echo "[-] Engine missing: ${ENGINE}" >&2
    exit 1
fi

SXS_POOL=""
if [[ -d '/run/media/ron/C8FC2BF4FC2BDB86/$WINDOWS.~BT/NewOS/Windows/WinSxS/' ]]; then
    SXS_POOL='/run/media/ron/C8FC2BF4FC2BDB86/$WINDOWS.~BT/NewOS/Windows/WinSxS/'
elif [[ -d "$HOME/artifacts" ]]; then
    SXS_POOL="$HOME/artifacts"
elif [[ -d "$HOME/downloads" ]]; then
    SXS_POOL="$HOME/downloads"
else
    SXS_POOL="$HOME"
fi

echo "[*] Targeted Forensic Root: ${SXS_POOL}"

TOTAL=0
OPTIMAL=0
REJECTED=0

while IFS= read -r -d '' target; do
    TOTAL=$((TOTAL + 1))
    echo "=== [${TOTAL}] Auditing: ${target} ==="

    set +e
    "${ENGINE}" "${target}"
    STATUS=$?
    set -e

    if [[ ${STATUS} -eq 66 ]]; then
        OPTIMAL=$((OPTIMAL + 1))
    else
        REJECTED=$((REJECTED + 1))
    fi
done < <(find "${SXS_POOL}" -maxdepth 3 -type f \( -iname "*.dll" -o -iname "*.sys" -o -iname "*.exe" \) -print0 2>/dev/null)

echo "=================================================="
echo " ATLAS SUMMARY: Total: ${TOTAL} | Optimal (0x42): ${OPTIMAL} | Rejected/Fault: ${REJECTED}"
echo "=================================================="
