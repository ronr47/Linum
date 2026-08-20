#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "      DEPLOYING CYBER-LINEAR 2026 SHELL ENVIRONMENT         "
echo "============================================================"

BASHRC="$HOME/.bashrc"
BACKUP="$HOME/.bashrc.backup.$(date +%Y%m%d_%H%M%S)"
cp "$BASHRC" "$BACKUP"
echo "Backup created at: $BACKUP"

cat << 'SHELL_EOF' >> "$BASHRC"

# ==============================================================================
# LINUM // CYBER-LINEAR 2026 SHELL ENGINE
# ==============================================================================

# Truecolor ANSI Definitions
export C_RESET="\[\033[0m\]"
export C_BOLD="\[\033[1m\]"
export C_DIM="\[\033[2m\]"
export C_AQUA="\[\033[38;2;0;255;240m\]"
export C_MAGENTA="\[\033[38;2;255;0;128m\]"
export C_GREEN="\[\033[38;2;57;255;20m\]"
export C_BLUE="\[\033[38;2;0;150;255m\]"
export C_PURPLE="\[\033[38;2;180;100;255m\]"
export C_AMBER="\[\033[38;2;255;170;0m\]"
export C_DARK="\[\033[38;2;70;70;90m\]"

# Git Status Indicator
parse_git_branch() {
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || return
    if [[ $(git status --porcelain 2>/dev/null) ]]; then
        echo -e " \033[38;2;255;0;128m⬡ [${branch}*]\033[0m"
    else
        echo -e " \033[38;2;57;255;20m⬢ [${branch}]\033[0m"
    fi
}

# Dynamic Prompt Construction
set_linum_prompt() {
    local EXIT_CODE="$?"
    local STATUS_COLOR="$C_GREEN"
    if [ "$EXIT_CODE" -ne 0 ]; then
        STATUS_COLOR="$C_MAGENTA"
    fi

    local VENV_INDICATOR=""
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        VENV_INDICATOR="${C_PURPLE}(linum-env)${C_RESET} "
    fi

    PS1="${VENV_INDICATOR}${C_AQUA}ron${C_DARK}@${C_BLUE}host${C_RESET} ${C_DARK}::${C_RESET} ${C_BOLD}${C_AQUA}\w${C_RESET}\$(parse_git_branch)\n${STATUS_COLOR}❯${C_RESET} "
}

PROMPT_COMMAND=set_linum_prompt

# Workflow Aliases
alias lgate="cd ~/linum && ./linum_truth_gate.sh"
alias ltest="cd ~/linum && python -m pytest -q"
alias lvis="linum --visual"
alias lrust="cd ~/linum && linum --rust"
alias cls="clear && linum_welcome"

# Interactive Welcome Banner
linum_welcome() {
    echo -e "\033[38;2;180;100;255m╭─────────────────────────────────────────────────────────────────────────────╮\033[0m"
    echo -e "\033[38;2;180;100;255m│ \033[1m\033[38;2;0;255;240mLINUM SHELL KERNEL // ACTIVE NODE MATRIX\033[0m\033[38;2;180;100;255m                                    │\033[0m"
    echo -e "\033[38;2;180;100;255m│ \033[2mNode Target: x86_64-baremetal • eBPF-XDP • Subsystem: 100% Sound\033[0m\033[38;2;180;100;255m            │\033[0m"
    echo -e "\033[38;2;180;100;255m╰─────────────────────────────────────────────────────────────────────────────╯\033[0m"
}

linum_welcome
SHELL_EOF

echo "Reloading shell configuration..."
source "$BASHRC" 2>/dev/null || true
echo "=== Shell Environment Loaded ==="
