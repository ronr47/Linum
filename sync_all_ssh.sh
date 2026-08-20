#!/usr/bin/env bash
set -uo pipefail

USERNAME="ronr47"
BASE_DIR="${HOME}"

declare -A REPO_MAP=(
    ["linum"]="Linum"
    ["hyper-tower-server"]="hyper-tower-server"
    ["nexus-simulator"]="nexus-simulator"
    ["nexus-ultra-core"]="nexus-ultra-core"
    ["my-auto-scroller"]="my-auto-scroller"
    ["custom-shell"]="custom-shell"
    ["kv-store"]="kv-store"
    ["test-repo"]="test-repo"
)

echo "============================================================"
echo " ⚡ REPAIRING & SYNCHRONIZING REPOSITORIES VIA SSH"
echo "============================================================"

for local_folder in "${!REPO_MAP[@]}"; do
    remote_repo="${REPO_MAP[$local_folder]}"
    target_path="${BASE_DIR}/${local_folder}"

    if [ ! -d "${target_path}" ]; then
        continue
    fi

    echo ""
    echo "── Processing [${local_folder}] ──>"
    cd "${target_path}"

    # 1. Clean nested .git folders to prevent submodule indexing traps
    find . -mindepth 2 -name ".git" -type d -prune -exec rm -rf {} + 2>/dev/null || true

    # 2. Re-point remote to authenticated SSH
    ssh_url="git@github.com:${USERNAME}/${remote_repo}.git"
    git remote remove origin 2>/dev/null || true
    git remote add origin "${ssh_url}"
    echo "  [✔] Remote configured: ${ssh_url}"

    # 3. Standardize branch to main
    git branch -M main 2>/dev/null || true

    # 4. Stage and commit safely
    git add -A 2>/dev/null || true
    if [ -n "$(git status --porcelain)" ]; then
        git commit -m "Synchronize workspace and seal production build" -q 2>/dev/null || true
        echo "  [✔] Changes committed."
    fi

    # 5. Push to GitHub
    echo "  [*] Pushing to origin/main via SSH..."
    if git push -u origin main --force; then
        echo "  [✔] Synchronized: ${USERNAME}/${remote_repo}"
    else
        echo "  [!] Push failed for ${local_folder}."
    fi
done

echo ""
echo "============================================================"
echo " ⚡ ALL REPOSITORIES PROCESSED"
echo "============================================================"
