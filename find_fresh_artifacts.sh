#!/usr/bin/env bash
# ==============================================================================
# FRESH ARTIFACT TRACKER
# Purpose: Locates newly compiled engine binaries across all sub-folders
# ==============================================================================

set -euo pipefail

BLUE='\033[1;34m'
GREEN='\033[0;32m'
NC='\033[0m'

log_status() { echo -e "${BLUE}[*] ${1}${NC}"; }
log_found()  { echo -e "${GREEN}[✔] ${1}${NC}"; }

WORKSPACE="$HOME/linum"
cd "$WORKSPACE"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}          SCANNING FOR RECENTLY GENERATED ENGINE ARTIFACTS            ${NC}"
echo -e "${BLUE}======================================================================${NC}"

log_status "Searching for machine binaries or objects modified in the last 5 minutes..."

# Find files modified less than 5 minutes ago (-mmin -5), ignoring virtual environments
find . -type f -mmin -5 \
    -not -path '*/.*' \
    -not -path './linum-env*' \
    -not -path './venv*' \
    -not -path './find_fresh_artifacts.sh*' | while read -r fresh_file; do
    
    FILE_DETAILS=$(file "$fresh_file")
    FILE_SIZE=$(du -sh "$fresh_file" | awk '{print $1}')
    
    log_found "${fresh_file} (${FILE_SIZE})"
    echo "      Details: ${FILE_DETAILS}"
done

echo -e "${BLUE}======================================================================${NC}"
