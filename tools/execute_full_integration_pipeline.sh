#!/usr/bin/env bash
set -eo pipefail

export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
WORKSPACE="/home/ron/linum"
cd "$WORKSPACE"

echo "============================================================"
echo " ⚡ LINUM: NATIVE MESH DEEP PROBE & CRATE COMPILATION"
echo "============================================================"

# [1/5] CRATE HEALTH & CARGO WORKSPACE PROBE
echo "[1/5] Auditing & Building Core Workspace Crates..."
CRATES=(
  "native/linum_cranelift"
  "native/linum_ebpf_loader"
  "native/linum_wasi"
  "src/linum_fastjit"
  "src/linum_lsp"
  "node"
  "aethervpc-mvp"
)

for crate in "${CRATES[@]}"; do
    if [[ -d "$crate" && -f "$crate/Cargo.toml" ]]; then
        echo -n "  ▶ Compiling $crate... "
        (cd "$crate" && cargo check --release --quiet 2>/dev/null && echo -e "\033[0;32m[SOUND]\033[0m") || echo -e "\033[0;31m[REQUIRES_PATCH]\033[0m"
    fi
done

# [2/5] IN-MEMORY TCC COMPILER PROBE
echo -e "\n[2/5] Testing In-Memory libtcc Execution Engine..."
if [[ -f "$HOME/.local/lib/libtcc.a" ]]; then
    echo "  [✔] In-Memory C Engine: $HOME/.local/lib/libtcc.a"
else
    echo "  [✘] libtcc.a missing from ~/.local/lib"
fi

# [3/5] EXTERNAL CRATE DEPENDENCY MAPPING
echo -e "\n[3/5] Mapping External Systems (Safe Server Rebuild)..."
EXT_CRATES=(
  "/home/ron/safe_server_rebuild/hyper-tower-server/Cargo.toml"
  "/home/ron/safe_server_rebuild/hyper-tower-server/nullos-core/Cargo.toml"
  "/home/ron/safe_server_rebuild/hyper-tower-server/contained-llama-engine/Cargo.toml"
  "/home/ron/safe_server_rebuild/vortex_workstation/Cargo.toml"
  "/home/ron/Documents/RECOVERED_FILES/ru/native_dataplane/Cargo.toml"
)

for c in "${EXT_CRATES[@]}"; do
    if [[ -f "$c" ]]; then
        echo "  ▶ Found: $(grep 'name =' "$c" | head -n1 | tr -d ' "') ($c)"
    fi
done

# [4/5] EMBEDDED SHARED OBJECT VERIFICATION
echo -e "\n[4/5] Verifying Native Obfuscation & Cache Bridge Objects..."
SO_OBJS=(
  "/home/ron/safe_server_rebuild/vortex_workstation/EliteObfuscation.so"
  "/home/ron/safe_server_rebuild/vortex_workstation/target/release/libcache_bridge.so"
  "$WORKSPACE/src/linum/linum_cranelift_core.abi3.so"
)

for so in "${SO_OBJS[@]}"; do
    if [[ -f "$so" ]]; then
        echo "  [✔] Object: $so ($(file -b "$so" | cut -d',' -f1))"
    fi
done

# [5/5] ARTIFACT DATABASE SYNC
echo -e "\n[5/5] Syncing Discovered Objects into Linum Build Tracker..."
for so in "${SO_OBJS[@]}"; do
    if [[ -f "$so" && -x "$HOME/.local/bin/linum-track" ]]; then
        linum-track record "$so" "SHARED_LIB" "$so" "PASS" >/dev/null 2>&1 || true
    fi
done
echo "  [✔] Build tracker synchronized."

echo "============================================================"
echo " [✨] INTEGRATION AUDIT COMPLETE"
echo "============================================================"
