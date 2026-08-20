#!/usr/bin/env bash
set -euo pipefail

EMAIL="tatulatu700@gmail.com"
KEY_FILE="${HOME}/.ssh/id_ed25519"

echo "============================================================"
echo "    🔐 GITHUB AUTHENTICATION & REMOTE BIND ENGINE           "
echo "============================================================"

# [1/4] Generate Ed25519 SSH Key if not present
mkdir -p "${HOME}/.ssh"
chmod 700 "${HOME}/.ssh"

if [ ! -f "${KEY_FILE}" ]; then
    echo "[1/4] Generating new Ed25519 SSH key for ${EMAIL}..."
    ssh-keygen -t ed25519 -C "${EMAIL}" -f "${KEY_FILE}" -N ""
else
    echo "[1/4] Existing SSH key found at ${KEY_FILE}."
fi

# [2/4] Register Key with Local SSH Agent
echo "[2/4] Starting ssh-agent and loading identity..."
eval "$(ssh-agent -s)" > /dev/null
ssh-add "${KEY_FILE}" 2>/dev/null || true

# [3/4] Display Public Key for GitHub Registration
echo ""
echo "============================================================"
echo "📋 COPY THE PUBLIC KEY BELOW AND ADD TO GITHUB:"
echo "   👉 https://github.com/settings/ssh/new"
echo "============================================================"
cat "${KEY_FILE}.pub"
echo "============================================================"
echo ""

# [4/4] Prompt for GitHub Username and Repo Name to set Origin
read -r -p "Enter your GitHub Username: " GH_USER
read -r -p "Enter your Repository Name: " GH_REPO

if [ -n "${GH_USER}" ] && [ -n "${GH_REPO}" ]; then
    git remote remove origin 2>/dev/null || true
    git remote add origin "git@github.com:${GH_USER}/${GH_REPO}.git"
    echo "      [✔] Remote 'origin' bound to: git@github.com:${GH_USER}/${GH_REPO}.git"
fi

