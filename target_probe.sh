#!/usr/bin/env bash
# ==============================================================================
# TARGETED AUDIT: LINUM ENGINE, VOLT CONFIG, AND HIMARA /OPT BINARY
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m'

log_section() { echo -e "\n${BLUE}=== [TARGET: $1] ===${NC}"; }
log_item()    { echo -e "  ${BLUE}[*]${NC} $1"; }
log_success() { echo -e "  ${GREEN}[✔]${NC} $1"; }
log_warn()    { echo -e "  ${YELLOW}[!]${NC} $1"; }
log_critical(){ echo -e "  ${RED}[✘]${NC} $1"; }

# ------------------------------------------------------------------------------
# TARGET 1: ~/linum Repository Environment Audit
# ------------------------------------------------------------------------------
log_section "LINUM SYSTEM ARCHITECTURE (~/linum)"

if [ -d "$HOME/linum" ]; then
    log_success "Found local linum ecosystem path at: $HOME/linum"
    cd "$HOME/linum"
    
    # Check Python Virtual Environment isolation status
    if [ -d "linum-env" ] || [ -f ".venv/bin/activate" ]; then
        log_success "Active virtual environment environment detected."
    else
        log_warn "Missing explicit isolated virtual environment directory inside project structure."
    fi
    
    # Check Git layout or uncommitted changes modifying orchestration logic
    if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
        log_item "Current branch: $(git branch --show-current 2>/dev/null || echo 'detached')"
        MODIFIED_FILES=$(git status --porcelain | wc -l)
        log_item "Uncommitted/modified tracking files: ${MODIFIED_FILES}"
    else
        log_warn "Project path is not version-controlled via git."
    fi
else
    log_critical "Specified linum workspace not found at expected path: $HOME/linum"
fi

# ------------------------------------------------------------------------------
# TARGET 2: Vault / Volt System Search
# ------------------------------------------------------------------------------
log_section "CRYPTOGRAPHIC VOLT / VAULT DISCOVERY"

# Search for common naming variations of the vault inside your working environment
VOLT_PATHS=$(find "$HOME" -maxdepth 3 -type d \( -name "*volt*" -o -name "*vault*" \) 2>/dev/null || true)

if [ -n "$VOLT_PATHS" ]; then
    echo "$VOLT_PATHS" | while read -r volt_path; do
        log_success "Discovered secure node target: ${volt_path}"
        # Audit permissions: Vault directories should strictly be 700 or 600
        PERMS=$(stat -c "%a" "${volt_path}")
        OWNER=$(stat -c "%U:%G" "${volt_path}")
        log_item "Permissions: ${PERMS} | Owner: ${OWNER}"
        
        if [ "$PERMS" -gt 700 ]; then
            log_critical "Security Breach: Vault path is readable by other local system accounts!"
        else
            log_success "Access parameters locked down correctly."
        fi
    done
else
    log_warn "No directory matching 'volt' or 'vault' resolved in user directory structure."
fi

# ------------------------------------------------------------------------------
# TARGET 3: /opt/himara Security Audit
# ------------------------------------------------------------------------------
log_section "HIMARA CORE SERVICE INTERACTION (/opt)"

HIMARA_DIR="/opt/himara"
if [ -d "$HIMARA_DIR" ]; then
    log_success "Himara target directory verified at: ${HIMARA_DIR}"
    
    # Inventory binaries and configurations
    log_item "Directory contents inventory:"
    ls -la "${HIMARA_DIR}" | sed 's/^/    /'
    
    # Trace execution loops, processes, or systemd hooks mapping back to this tool
    log_item "Analyzing live process map for Himara tasks..."
    HIMARA_PROC=$(ps aux | grep -i "himara" | grep -v "grep" || true)
    if [ -n "$HIMARA_PROC" ]; then
        log_success "Active executing process found:"
        echo "${HIMARA_PROC}" | sed 's/^/    /'
    else
        log_warn "Himara binary is currently idle or service structure is down."
    fi
    
    # Check for linked systemd automation profiles
    if [ -f "/etc/systemd/system/himara.service" ]; then
        log_success "Systemd initialization daemon profile found at /etc/systemd/system/himara.service"
        log_item "Service state: $(systemctl is-active himara 2>/dev/null || echo 'inactive')"
    fi
else
    log_critical "Himara workspace missing from host at path: ${HIMARA_DIR}"
fi

echo -e "\n${BLUE}=== [TARGET AUDIT PIPELINE CONCLUDED] ===${NC}"
