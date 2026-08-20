#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"
cd "${ROOT_DIR}"

GITHUB_USER="tatulatu700-lang"
REPO_NAME="linum"

echo "============================================================"
echo "    🚀 LINUM CORE: GITHUB SSH AUTH & REMOTE SYNC          "
echo "============================================================"

# [1/4] Ensure Modern ED25519 SSH Key Exists
mkdir -p ~/.ssh
chmod 700 ~/.ssh

if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo "[1/4] Generating dedicated ED25519 SSH key..."
    ssh-keygen -t ed25519 -C "tatulatu700@gmail.com" -f ~/.ssh/id_ed25519 -N ""
else
    echo "[1/4] Existing SSH key located at ~/.ssh/id_ed25519."
fi

# [2/4] Display Public Key for One-Time Web Registration
echo ""
echo "------------------------------------------------------------"
echo "🔑 COPY THE PUBLIC KEY BELOW (Add to: https://github.com/settings/keys):"
echo "------------------------------------------------------------"
cat ~/.ssh/id_ed25519.pub
echo "------------------------------------------------------------"
echo ""

# [3/4] Configure Git User & Correct Remote URL
echo "[3/4] Setting Git identities and canonical remote path..."
git config --global user.name "${GITHUB_USER}"
git config --global user.email "tatulatu700@gmail.com"

# Bind full SSH path (using port 443 config already installed)
git remote remove origin 2>/dev/null || true
git remote add origin "git@github.com:${GITHUB_USER}/${REPO_NAME}.git"

echo "      [✔] Remote bound: git@github.com:${GITHUB_USER}/${REPO_NAME}.git"

# [4/4] Commit Workspace State & Push
echo "[4/4] Finalizing workspace snapshot and pushing..."
git add -A
git commit -m "feat(core): v1.0.0-PROD sealed compilation runtimes (LLVM/MLIR/WASI/AVX-512)" 2>/dev/null || echo "      [i] Working tree already clean."

echo ""
echo "Attempting upstream synchronization..."
if git push -u origin master --force; then
    echo "============================================================"
    echo "      ✔ CODEBASE SYNCHRONIZED SUCCESSFULLY TO GITHUB       "
    echo "============================================================"
else
    echo "============================================================"
    echo "  [!] Action Required:"
    echo "  1. Copy the public key printed above into GitHub Settings -> SSH Keys."
    echo "  2. Ensure the repository '${REPO_NAME}' exists under github.com/${GITHUB_USER}."
    echo "  3. Re-run: git push -u origin master --force"
    echo "============================================================"
fi
