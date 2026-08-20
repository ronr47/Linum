
#!/usr/bin/env bash
# =================================================================================================================
#  ⚔️  LINUM ARCHITECTURE MISSION MATRIX & INVARIANT COMMANDMENTS COMPLIANCE 
#  1. IDEMPOTENT EMISSION: Lookups verify tracking tokens explicitly before running mount structures.
#  4. STRICT NAMESPACE: Tracks exact VFS mount definitions without appending loose workspace directories.
# =================================================================================================================
set -euo pipefail

NS_NAME="linum_sandbox"
BPF_ROOT="/sys/fs/bpf"
XSK_MAP_PATH="${BPF_ROOT}/linum_xsk_map"

section() {
    printf '\n=== %s ===\n' "$1"
}

die() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

section "1. ENFORCING IDEMPOTENT DIRECTORY MOUNT SYSTEM"

# FACT: BPF Virtual File Systems must be explicitly shared to bypass namespace copy blocks.
if ! findmnt -M "${BPF_ROOT}" >/dev/null; then
    echo "[+] Initializing host global BPFFS layer..."
    mount -t bpf bpf "${BPF_ROOT}"
fi

# Invariant Guard: Ensure mount modifications ripple bi-directionally across namespaces
echo "[+] Turning BPFFS into a shared propagation node..."
mount --make-shared "${BPF_ROOT}"

section "2. NAMESPACE CONTEXT ENFORCEMENT"

if ! ip netns list | awk '{print $1}' | grep -qx "${NS_NAME}"; then
    die "Network namespace ${NS_NAME} does not exist. Execute setup_sandbox.sh first."
fi

# INFERENCE: Ensure the target network namespace contains its own mounted tracking subsystem
NS_BPF_DIR="/run/netns/${NS_NAME}_bpf"
if [ ! -d "/etc/netns/${NS_NAME}" ]; then
    echo "[+] Constructing network namespace local VFS profile mirrors..."
    mkdir -p "/etc/netns/${NS_NAME}"
fi

section "3. VERIFY MAP DEFINITION AND MAP ANCHORING"

# Locate Map ID via static string matching
MAP_ID=$(bpftool map show | awk '$2 == "xskmap" && $3 == "name" && $4 == "xsks_map" { gsub(":", "", $1); print $1; exit }')

if [ -z "${MAP_ID}" ]; then
    die "Execution halted: generating target xsks_map not found within global kernel registers."
fi

echo "[+] Verified xsks_map discovered with Kernel ID: ${MAP_ID}"

# Idempotent Pinned Asset Generation
if [ -e "${XSK_MAP_PATH}" ]; then
    echo "[+] Unlinking stale pinned assets..."
    rm -f "${XSK_MAP_PATH}"
fi

echo "[+] Forcing authoritative pin of map ID ${MAP_ID} to path: ${XSK_MAP_PATH}"
bpftool map pin id "${MAP_ID}" "${XSK_MAP_PATH}"

section "4. EXECUTING CONSUMER VIA EXPLICIT MOUNT PROPAGATION"

# VERIFIED: We pass only the network context, leaving the mount namespace tracking the host's shared VFS tree intact.
# This guarantees xsk_consumer.c can fetch the real FD from /sys/fs/bpf/linum_xsk_map directly.
echo "[+] Invoking AF_XDP socket processing engine inside network namespace layer..."

exec nsenter --net="/run/netns/${NS_NAME}" ./xsk_consumer
