#!/usr/bin/env bash
set -uo pipefail

USERNAME="ronr47"
BASE_DIR="${HOME}"

# Map of known local repository paths to their exact GitHub repo names
declare -A REPO_MAP=(
    ["linum"]="Linum"
    ["my-auto-scroller"]="my-auto-scroller"
    ["hyper-tower-server"]="hyper-tower-server"
    ["nexus-simulator"]="nexus-simulator"
    ["nexus-ultra-core"]="nexus-ultra-core"
    ["custom-shell"]="custom-shell"
    ["kv-store"]="kv-store"
    ["test-repo"]="test-repo"
)

echo "============================================================"
echo " ⚡ GITHUB REPOSITORY AUDIT & REPAIR UTILITY"
echo " Target Account: ${USERNAME}"
echo "============================================================"

for local_folder in "${!REPO_MAP[@]}"; do
    remote_repo="${REPO_MAP[$local_folder]}"
    target_path="${BASE_DIR}/${local_folder}"

    echo ""
    echo "── Checking [${local_folder}] ──>"

    if [ ! -d "${target_path}" ]; then
        echo "  [!] Folder ${target_path} not found locally. Skipping."
        continue
    fi

    cd "${target_path}"

    # 1. Initialize git if missing
    if [ ! -d ".git" ]; then
        echo "  [*] Initializing git repository..."
        git init -q
    fi

    # 2. Configure signature
    git config user.name "Ron"
    git config user.email "tatulatu700@gmail.com"

    # 3. Configure remote URL (using HTTPS with correct account/casing)
    target_url="https://github.com/${USERNAME}/${remote_repo}.git"
    git remote remove origin 2>/dev/null || true
    git remote add origin "${target_url}"
    echo "  [✔] Remote set: ${target_url}"

    # 4. Standardize branch name to main
    git branch -M main 2>/dev/null || true

    # 5. Check working tree status and stage untracked/modified files
    if [ -n "$(git status --porcelain)" ]; then
        echo "  [*] Staging uncommitted changes..."
        git add -A
        git commit -m "Chore: Synchronize workspace and seal production build" -q
        echo "  [✔] Local changes committed."
    else
        echo "  [✔] Working directory clean."
    fi

    # 6. Push to remote
    echo "  [*] Pushing to origin/main..."
    if git push -u origin main --force 2>/dev/null; then
        echo "  [✔] Successfully synchronized with GitHub (${USERNAME}/${remote_repo})."
    else
        echo "  [!] Push failed. Verify repository exists on GitHub or check network credentials."
    fi
done

echo ""
echo "============================================================"
echo " ⚡ ALL LOCAL REPOSITORIES AUDITED"
echo "============================================================"
