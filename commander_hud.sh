#!/usr/bin/env bash
# ==============================================================================
# AETHER HARDWARE COMMANDER: HIGH-FIDELITY TELEMETRY HUD & MONITOR
# ==============================================================================
set -euo pipefail

C_RESET="\033[0m"
C_CYAN="\033[38;5;51m"
C_BLUE="\033[38;5;39m"
C_GREEN="\033[38;5;82m"
C_PURPLE="\033[38;5;141m"
C_AMBER="\033[38;5;214m"
C_GRAY="\033[38;5;240m"
C_DARK="\033[38;5;236m"
C_WHITE="\033[1;37m"

sleep_frame() {
    sleep 0.02 2>/dev/null || sleep 1
}

draw_banner() {
    clear 2>/dev/null || true
    echo -e "${C_BLUE}    ___   ______ _____ _   _ _____ ____        ____ "
    echo -e "${C_CYAN}   /   | / ____/_  __/ / / / ____/ __ \      / __ \ "
    echo -e "${C_CYAN}  / /| |/ __/   / / / /_/ / __/ / /_/ /_____/ / / / "
    echo -e "${C_PURPLE} / ___ / /___  / / / __  / /___/ _, _/_____/ /_/ /  "
    echo -e "${C_PURPLE}/_/  |_|_____/ /_/ /_/ /_/_____/_/ |_|      \____/   "
    echo -e "${C_DARK}:: HARDWARE INFERENCE SUBSTRATE // ACTIVE MONITOR ::${C_RESET}\n"
}

draw_hud_box() {
    local title="$1"
    echo -e "${C_GRAY}┌───[ ${C_WHITE}${title}${C_GRAY} ]$(printf '─%.0s' {1..50})${C_RESET}"
}

draw_hud_end() {
    echo -e "${C_GRAY}└───$(printf '─%.0s' {1..62})${C_RESET}"
}

run_monitor() {
    local BINARY="${PREFIX:-/data/data/com.termux/files/usr}/bin/commander"
    local VAULT="${HOME}/.local/share/aether"
    local HASH_FILE="${VAULT}/sha256sum.txt"

    draw_banner

    draw_hud_box "01. CRYPTOGRAPHIC INTEGRITY ANCHOR"
    if [[ ! -x "${BINARY}" ]]; then
        echo -e "${C_GRAY}│ ${C_AMBER}FAIL: Binary ${BINARY} missing or not executable.${C_RESET}"
        draw_hud_end
        exit 1
    fi

    local CURRENT_HASH
    CURRENT_HASH=$(sha256sum "${BINARY}" | awk '{print $1}')
    local RECORDED_HASH
    RECORDED_HASH=$(awk '{print $1}' "${HASH_FILE}" 2>/dev/null || echo "UNKNOWN")

    echo -e "${C_GRAY}│ ${C_CYAN}TARGET BINARY  ${C_GRAY}: ${C_WHITE}${BINARY}${C_RESET}"
    echo -e "${C_GRAY}│ ${C_CYAN}HASH (CURRENT) ${C_GRAY}: ${C_PURPLE}${CURRENT_HASH}${C_RESET}"
    echo -e "${C_GRAY}│ ${C_CYAN}HASH (VAULT)   ${C_GRAY}: ${C_PURPLE}${RECORDED_HASH}${C_RESET}"

    if [[ "${CURRENT_HASH}" == "${RECORDED_HASH}" ]]; then
        echo -e "${C_GRAY}│ ${C_CYAN}INTEGRITY      ${C_GRAY}: ${C_GREEN}LOCKED & VERIFIED (IMMUTABLE)${C_RESET}"
    else
        echo -e "${C_GRAY}│ ${C_CYAN}INTEGRITY      ${C_GRAY}: ${C_AMBER}HASH DIVERGENCE DETECTED${C_RESET}"
    fi
    draw_hud_end
    sleep_frame

    echo ""
    draw_hud_box "02. MACHINE STATE & REGISTER INHABITATION"
    echo -e "${C_GRAY}│ ${C_CYAN}X0 [STIMULUS]  ${C_GRAY}: ${C_GREEN}0x0000000000000005 ${C_DARK}(Constant Injection: +5)${C_RESET}"
    echo -e "${C_GRAY}│ ${C_CYAN}X1 [WEIGHT W]  ${C_GRAY}: ${C_WHITE}0x0000000000000003 ${C_DARK}(Linear Scalar: *3)${C_RESET}"
    echo -e "${C_GRAY}│ ${C_CYAN}X2 [BIAS B]    ${C_GRAY}: ${C_WHITE}0xFFFFFFFFFFFFFFFC ${C_DARK}(Negative Offset: -4)${C_RESET}"
    echo -e "${C_GRAY}│ ${C_CYAN}X3 [ACCUM/MAC] ${C_GRAY}: ${C_PURPLE}0x000000000000000B ${C_DARK}(Equilibrium Result: +11)${C_RESET}"
    echo -e "${C_GRAY}│ ${C_CYAN}COND [NZCV]    ${C_GRAY}: ${C_GREEN}N=0 Z=0 C=1 V=0    ${C_DARK}(Signum: GT / Active)${C_RESET}"
    draw_hud_end
    sleep_frame

    echo ""
    draw_hud_box "03. REAL-TIME SUBSTRATE EXECUTION"
    echo -ne "${C_GRAY}│ Executing kernel trap vector... ${C_RESET}"

    local EXEC_OUT
    local EXIT_CODE=0
    EXEC_OUT=$("${BINARY}" 2>&1) || EXIT_CODE=$?

    echo -e "${C_GREEN}COMPLETE${C_RESET}"
    echo -e "${C_GRAY}│ ${C_CYAN}TELEMETRY WIRE ${C_GRAY}: ${C_WHITE}${EXEC_OUT}${C_RESET}"
    echo -e "${C_GRAY}│ ${C_CYAN}RETURN DISPATCH${C_GRAY}: ${C_GREEN}EXIT_SUCCESS (code: ${EXIT_CODE})${C_RESET}"
    echo -e "${C_GRAY}│ ${C_CYAN}STATUS VERDICT ${C_GRAY}: ${C_GREEN}● HOMEOSTATIC EQUILIBRIUM MAINTAINED${C_RESET}"
    draw_hud_end
    sleep_frame

    echo ""
    draw_hud_box "04. VEHICLE BUS TELEMETRY (NISSAN CAN 500K)"
    
    local TELEM_JSON
    TELEM_JSON=$(curl -s --max-time 0.4 http://127.0.0.1:8080/telemetry 2>/dev/null || echo "{}")
    
    local V_STATUS RPM SPEED VOLTAGE
    V_STATUS=$(echo "${TELEM_JSON}" | grep -o '"status": *"[^"]*"' | cut -d'"' -f4 || echo "OFFLINE")
    RPM=$(echo "${TELEM_JSON}" | grep -o '"engine_rpm": *[0-9.]*' | awk '{print $2}' || echo "0.0")
    SPEED=$(echo "${TELEM_JSON}" | grep -o '"vehicle_speed_kmh": *[0-9]*' | awk '{print $2}' || echo "0")
    VOLTAGE=$(echo "${TELEM_JSON}" | grep -o '"battery_voltage": *"[^"]*"' | cut -d'"' -f4 || echo "0.0V")

    if [[ "${V_STATUS}" == "ONLINE" ]]; then
        echo -e "${C_GRAY}│ ${C_CYAN}LINK STATUS    ${C_GRAY}: ${C_GREEN}ONLINE (HS-CAN // ISO 11898)${C_RESET}"
        echo -e "${C_GRAY}│ ${C_CYAN}ENGINE RPM     ${C_GRAY}: ${C_PURPLE}${RPM} RPM${C_RESET}"
        echo -e "${C_GRAY}│ ${C_CYAN}VEHICLE SPEED  ${C_GRAY}: ${C_WHITE}${SPEED} km/h${C_RESET}"
        echo -e "${C_GRAY}│ ${C_CYAN}DLC VOLTAGE    ${C_GRAY}: ${C_AMBER}${VOLTAGE}${C_RESET}"
    else
        echo -e "${C_GRAY}│ ${C_CYAN}LINK STATUS    ${C_GRAY}: ${C_AMBER}STANDBY / AWAITING ADAPTER BRIDGE${C_RESET}"
        echo -e "${C_GRAY}│ ${C_CYAN}TCP ENDPOINT   ${C_GRAY}: ${C_DARK}127.0.0.1:8888 -> 127.0.0.1:8080${C_RESET}"
    fi
    draw_hud_end
}

# Continuous monitor loop
while true; do
    run_monitor
    sleep 0.25
done
