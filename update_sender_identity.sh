#!/usr/bin/env bash
# ==============================================================================
# SENDER IDENTITY HARMONIZATION ENGINE
# Purpose: Explicitly anchors your verified identity across all sales manifests
# ==============================================================================

set -euo pipefail

BLUE='\033[1;34m'
GREEN='\033[0;32m'
NC='\033[0m'

MY_EMAIL="ronrnlds47@gmail.com"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}          SYNCHRONIZING SENDER PROFILE ENVELOPE                        ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Update the local msmtp terminal mail router settings if config exists
if [ -f "$HOME/.config/msmtp/config" ]; then
    sed -i "s|^from .*|from             ${MY_EMAIL}|" "$HOME/.config/msmtp/config"
    sed -i "s|^user .*|user             ${MY_EMAIL}|" "$HOME/.config/msmtp/config"
    log_status "msmtp configuration profile sender records aligned."
fi

# 2. Inject your signature dynamically into all active pitch manifests
for pitch in ~/linum/build/artifacts/*_pitch.txt; do
    if [ -f "$pitch" ]; then
        # Replace template placeholders or strip raw sender lines to inject exact email coordinates
        if ! grep -q "${MY_EMAIL}" "$pitch"; then
            sed -i "s|Low-Level Systems Engineer|Low-Level Systems Engineer\nEmail: ${MY_EMAIL}|g" "$pitch"
            sed -i "s|Low-Level Systems Developer|Low-Level Systems Developer\nEmail: ${MY_EMAIL}|g" "$pitch"
        fi
    fi
done

echo -e "${GREEN}[✔] Sender identity synchronized globally across your deployment workspace.${NC}"
echo -e "    Active Sender Contact: \033[1;33m${MY_EMAIL}\033[0m"
echo -e "${BLUE}======================================================================${NC}"
