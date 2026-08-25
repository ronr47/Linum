#!/usr/bin/env bash
# ==============================================================================
# LINUM WORKSPACE ARCHITECTURE AND INTEGRITY PROBE
# ==============================================================================

set -euo pipefail

BLUE='\033[1;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_status() { echo -e "${BLUE}[*] ${1}${NC}"; }
log_pass()   { echo -e "${GREEN}[✔] ${1}${NC}"; }
log_warn()   { echo -e "${YELLOW}[!] ${1}${NC}"; }

WORKSPACE="$HOME/linum"
cd "$WORKSPACE"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}          ANALYZING ACTIVE LINUM DEVELOPMENT ECOSYSTEM                ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Map Directory Tree Topologies (Ignoring virtual environments to avoid bloat)
log_status "Analyzing project folder structure..."
find . -maxdepth 2 -type d \
    -not -path '*/.*' \
    -not -path './linum-env*' \
    -not -path './.venv*' \
    -not -path './himara_mount*' | sed 's/^/  /'

# 2. Identify Primary Execution Entry Points
log_status "Detecting core execution binaries and orchestration drivers..."
CORE_FILES=$(find . -maxdepth 2 \( -name "*.py" -o -name "*.sh" \) \
    -not -path '*/.*' \
    -not -path './linum-env*' \
    -not -path './target_probe.sh*' \
    -not -path './inspect_linum_core.sh*' 2>/dev/null || true)

if [ -n "$CORE_FILES" ]; then
    echo "${CORE_FILES}" | sed 's/^/  [✔] Found: /'
else
    log_warn "No top-level Python or Bash script engines resolved in the project root."
fi

# 3. Audit Python Environment Package Dependencies
log_status "Checking active pip/virtualenv dependency manifest..."
if [ -f "requirements.txt" ]; then
    log_pass "Found production requirements.txt entry points:"
    cat requirements.txt | sed 's/^/    /'
elif [ -f "pyproject.toml" ]; then
    log_pass "Found pyproject.toml configuration layer."
else
    log_warn "Missing explicit packages manifest (requirements.txt). Dependencies may be unmanaged."
fi

# 4. Target the 221 Uncommitted Files for Data Leak Hazards
log_status "Scanning untracked workspace metadata for hardcoded keys or secrets..."
# Search for standard high-risk patterns in uncommitted code blocks
if command -v git >/dev/null 2>&1 && [ -d ".git" ]; then
    LEAK_CHECK=$(git status --porcelain | awk '{print $2}' | xargs -I {} grep -HnE '(API_KEY|SECRET|PASSWORD|PRIVATE_KEY|PASSPHRASE)[[:space:]]*=' {} 2>/dev/null || true)
    if [ -n "$LEAK_CHECK" ]; then
        log_warn "Potential exposed configuration keys discovered in uncommitted files:\n${LEAK_CHECK}"
    else
        log_pass "Clean tracking state. No obvious credential structures exposed in your uncommitted files."
    fi
else
    log_warn "Git status unavailable. Skipping uncommitted leak analysis loop."
fi

echo -e "${BLUE}======================================================================${NC}"
