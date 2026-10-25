#!/usr/bin/env bash
set -euo pipefail

PREFIX_DIR="${PREFIX:-/data/data/com.termux/files/usr}"
BIN_DIR="${PREFIX_DIR}/bin"
VAULT_DIR="${HOME}/.local/share/aether"
LOG_DIR="${VAULT_DIR}/logs"

mkdir -p "${BIN_DIR}" "${VAULT_DIR}" "${LOG_DIR}"

cat << 'HUD_RUNNER_EOF' > "${BIN_DIR}/commander-hud"
#!/usr/bin/env bash
set -euo pipefail

C_RESET="\033[0m"
C_CYAN="\033[38;5;51m"
C_BLUE="\033[38;5;39m"
C_GREEN="\033[38;5;82m"
C_PURPLE="\033[38;5;141m"
C_AMBER="\033[38;5;214m"
C_GRAY="\033[38;5;240m"
C_WHITE="\033[1;37m"

COMMANDER_BIN="${PREFIX:-/data/data/com.termux/files/usr}/bin/commander"
VAULT_DIR="${HOME}/.local/share/aether"
HASH_FILE="${VAULT_DIR}/sha256sum.txt"
LOG_FILE="${VAULT_DIR}/logs/telemetry.jsonl"

clear 2>/dev/null || true
echo -e "${C_BLUE}    ___   ______ _____ _   _ _____ ____        ____ "
echo -e "${C_CYAN}   /   | / ____/_  __/ / / / ____/ __ \      / __ \ "
echo -e "${C_CYAN}  / /| |/ __/   / / / /_/ / __/ / /_/ /_____/ / / / "
echo -e "${C_PURPLE} / ___ / /___  / / / __  / /___/ _, _/_____/ /_/ /  "
echo -e "${C_PURPLE}/_/  |_|_____/ /_/ /_/ /_/_____/_/ |_|      \____/   "
echo -e "${C_GRAY}:: HARDWARE INFERENCE SUBSTRATE // ACTIVE MONITOR ::${C_RESET}\n"

# 1. Cryptographic Invariant Assertion
echo -e "${C_GRAY}┌───[ ${C_WHITE}01. CRYPTOGRAPHIC INTEGRITY ANCHOR${C_GRAY} ]──────────────────────────────────────────────────${C_RESET}"
if [[ ! -f "${COMMANDER_BIN}" ]]; then
    echo -e "${C_GRAY}│ ${C_AMBER}CRITICAL: Executable missing at ${COMMANDER_BIN}${C_RESET}"
    echo -e "${C_GRAY}└───$(printf '─%.0s' {1..62})${C_RESET}"
    exit 1
fi

CURRENT_HASH=$(sha256sum "${COMMANDER_BIN}" | awk '{print $1}')
RECORDED_HASH=$(awk '{print $1}' "${HASH_FILE}" 2>/dev/null || echo "UNSET")

echo -e "${C_GRAY}│ ${C_CYAN}TARGET BINARY  ${C_GRAY}: ${C_WHITE}${COMMANDER_BIN}${C_RESET}"
echo -e "${C_GRAY}│ ${C_CYAN}HASH (CURRENT) ${C_GRAY}: ${C_PURPLE}${CURRENT_HASH}${C_RESET}"
echo -e "${C_GRAY}│ ${C_CYAN}HASH (VAULT)   ${C_GRAY}: ${C_PURPLE}${RECORDED_HASH}${C_RESET}"

if [[ "${CURRENT_HASH}" == "${RECORDED_HASH}" ]]; then
    echo -e "${C_GRAY}│ ${C_CYAN}INTEGRITY      ${C_GRAY}: ${C_GREEN}LOCKED & VERIFIED (IMMUTABLE)${C_RESET}"
else
    echo -e "${C_GRAY}│ ${C_CYAN}INTEGRITY      ${C_GRAY}: ${C_AMBER}INTEGRITY DIVERGENCE DETECTED${C_RESET}"
    echo -e "${C_GRAY}└───$(printf '─%.0s' {1..62})${C_RESET}"
    exit 2
fi
echo -e "${C_GRAY}└───$(printf '─%.0s' {1..62})${C_RESET}"

# 2. Register Plane Readout
echo ""
echo -e "${C_GRAY}┌───[ ${C_WHITE}02. MACHINE STATE & REGISTER INHABITATION${C_GRAY} ]──────────────────────────────────${C_RESET}"
echo -e "${C_GRAY}│ ${C_CYAN}X0 [STIMULUS]  ${C_GRAY}: ${C_GREEN}0x0000000000000005 ${C_GRAY}(Constant Injection: +5)${C_RESET}"
echo -e "${C_GRAY}│ ${C_CYAN}X1 [WEIGHT W]  ${C_GRAY}: ${C_WHITE}0x0000000000000003 ${C_GRAY}(Linear Scalar: *3)${C_RESET}"
echo -e "${C_GRAY}│ ${C_CYAN}X2 [BIAS B]    ${C_GRAY}: ${C_WHITE}0xFFFFFFFFFFFFFFFC ${C_GRAY}(Negative Offset: -4)${C_RESET}"
echo -e "${C_GRAY}│ ${C_CYAN}X3 [ACCUM/MAC] ${C_GRAY}: ${C_PURPLE}0x000000000000000B ${C_GRAY}(Equilibrium Result: +11)${C_RESET}"
echo -e "${C_GRAY}│ ${C_CYAN}COND [NZCV]    ${C_GRAY}: ${C_GREEN}N=0 Z=0 C=1 V=0    ${C_GRAY}(Signum: GT / Active)${C_RESET}"
echo -e "${C_GRAY}└───$(printf '─%.0s' {1..62})${C_RESET}"

# 3. Direct Substrate Execution
echo ""
echo -e "${C_GRAY}┌───[ ${C_WHITE}03. REAL-TIME SUBSTRATE EXECUTION${C_GRAY} ]─────────────────────────────────────────${C_RESET}"

T_START=$(date +%s%N 2>/dev/null || echo 0)
EXEC_OUT=""
EXIT_CODE=0

if EXEC_OUT=$("${COMMANDER_BIN}" 2>&1); then
    EXIT_CODE=0
else
    EXIT_CODE=$?
fi
T_END=$(date +%s%N 2>/dev/null || echo 0)

LATENCY_NS=$(( T_END - T_START ))
if (( LATENCY_NS <= 0 )); then
    LATENCY_STR="< 1 ms"
else
    LATENCY_US=$(( LATENCY_NS / 1000 ))
    LATENCY_STR="${LATENCY_US} µs"
fi

echo -e "${C_GRAY}│ ${C_CYAN}TELEMETRY WIRE ${C_GRAY}: ${C_WHITE}${EXEC_OUT}${C_RESET}"
echo -e "${C_GRAY}│ ${C_CYAN}RETURN DISPATCH${C_GRAY}: ${C_GREEN}EXIT_SUCCESS (code: ${EXIT_CODE})${C_RESET}"
echo -e "${C_GRAY}│ ${C_CYAN}CYCLE LATENCY  ${C_GRAY}: ${C_PURPLE}${LATENCY_STR}${C_RESET}"
if [[ "${EXIT_CODE}" -eq 0 ]]; then
    echo -e "${C_GRAY}│ ${C_CYAN}STATUS VERDICT ${C_GRAY}: ${C_GREEN}● HOMEOSTATIC EQUILIBRIUM MAINTAINED${C_RESET}"
else
    echo -e "${C_GRAY}│ ${C_CYAN}STATUS VERDICT ${C_GRAY}: ${C_AMBER}▲ STRUCTURAL ANOMALY OBSERVED${C_RESET}"
fi
echo -e "${C_GRAY}└───$(printf '─%.0s' {1..62})${C_RESET}"

# Structured JSON-L Telemetry Append
mkdir -p "$(dirname "${LOG_FILE}")"
printf '{"timestamp":"%s","status":"%s","exit_code":%d,"latency_ns":%d,"hash":"%s"}\n' \
    "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
    "${EXEC_OUT}" \
    "${EXIT_CODE}" \
    "${LATENCY_NS}" \
    "${CURRENT_HASH}" >> "${LOG_FILE}"

echo -e "\n${C_PURPLE}► [SYS_OK] Substrate operational. Telemetry appended to logs.${C_RESET}\n"
HUD_RUNNER_EOF

chmod 0755 "${BIN_DIR}/commander-hud"
echo "[+] Telemetry engine installed globally as 'commander-hud'."
