#!/usr/bin/env bash
set -euo pipefail

C_RESET="\033[0m"
C_CYAN="\033[38;5;51m"
C_GREEN="\033[38;5;82m"
C_AMBER="\033[38;5;214m"
C_GRAY="\033[38;5;240m"

log_step() {
    printf "  ${C_GRAY}[${C_CYAN}%-12s${C_GRAY}]${C_RESET} %s\n" "$1" "$2"
}

echo -e "\n${C_CYAN}:: COMMENCING SYSTEM LOCKDOWN: AETHER HARDWARE COMMANDER ::${C_RESET}"

# 1. Target Directory Resolution
INSTALL_BIN="${PREFIX:-/data/data/com.termux/files/usr}/bin"
VAULT_DIR="${HOME}/.local/share/aether"

log_step "PROVISION" "Target Binary Path: ${INSTALL_BIN}"
log_step "PROVISION" "Target Vault Path:  ${VAULT_DIR}"

mkdir -p "${INSTALL_BIN}" "${VAULT_DIR}"

# 2. Assert Source Presence
if [[ ! -f "commander.elf" ]]; then
    echo -e "  ${C_AMBER}Error: commander.elf not found in current directory. Run run_all.sh first.${C_RESET}" >&2
    exit 1
fi

# 3. Secure Intermediate Artifacts to Vault
log_step "ARCHIVE" "Migrating toolchain assets into immutable vault..."
cp -f commander.a0 "${VAULT_DIR}/commander.a0" 2>/dev/null || true
cp -f commander.s "${VAULT_DIR}/commander.s" 2>/dev/null || true
cp -f aether0c.py "${VAULT_DIR}/aether0c.py" 2>/dev/null || true

# 4. Install and Lock Binary
log_step "INSTALL" "Installing standalone ELF to system path: ${INSTALL_BIN}/commander..."
cp -f commander.elf "${INSTALL_BIN}/commander"

log_step "LOCKDOWN" "Enforcing read-only execute permissions (0555)..."
chmod 0555 "${INSTALL_BIN}/commander"
chmod 0444 "${VAULT_DIR}/commander.a0" "${VAULT_DIR}/commander.s" 2>/dev/null || true
chmod 0555 "${VAULT_DIR}/aether0c.py" 2>/dev/null || true

# 5. Cryptographic Checksum Anchor
log_step "DIGEST" "Calculating SHA-256 binary hash anchor..."
sha256sum "${INSTALL_BIN}/commander" > "${VAULT_DIR}/sha256sum.txt"
HASH_VAL=$(awk '{print $1}' "${VAULT_DIR}/sha256sum.txt")
log_step "ANCHOR" "Hash: ${C_GREEN}${HASH_VAL}${C_RESET}"

# 6. Verification Trace
log_step "VERIFY" "Testing command execution via global system PATH..."
cd /
CMD_OUTPUT=$(commander)
CMD_EXIT=$?

if [[ "${CMD_EXIT}" -eq 0 && "${CMD_OUTPUT}" == "STATUS=EQUILIBRIUM" ]]; then
    echo -e "\n${C_GREEN}✔ HARDWARE COMMANDER PERMANENTLY LOCKED IN.${C_RESET}"
    echo -e "  Available globally as executable: ${C_CYAN}commander${C_RESET}"
    echo -e "  Immutable vault anchor:           ${C_CYAN}${VAULT_DIR}${C_RESET}\n"
else
    echo -e "\n  ${C_AMBER}Integrity validation failed.${C_RESET}" >&2
    exit 1
fi
