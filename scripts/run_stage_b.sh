#!/usr/bin/env bash
# run_stage_b.sh - Automated Stage B Blueprint (Simplified Mount Execution)

set -euo pipefail

MAP_ID=60
NS_NAME="linum_sandbox"
XSK_MAP_PATH="/sys/fs/bpf/linum_xsk_map"

echo "=== [SOPHIA-LINUM] STAGE B EXECUTION ENGINE ==="

# 1. Structural Checks
echo "[+] Checking Network Namespace Isolation Layer..."
if ! ip netns list | grep -q "${NS_NAME}"; then
    echo "[-] CRITICAL FAULT: Namespace '${NS_NAME}' absent."
    exit 1
fi

echo "[+] Verifying Kernel Ring 0 Map Allocation (ID: ${MAP_ID})..."
if ! sudo bpftool map show id "${MAP_ID}" &>/dev/null; then
    echo "[-] CRITICAL FAULT: XSKMAP instance ID ${MAP_ID} absent from Ring 0."
    exit 1
fi

# 2. Pin Map to the Global Host BPFFS Location Directly
echo "[+] Clearing legacy host handlers..."
sudo rm -f "${XSK_MAP_PATH}"

echo "[+] Pinning XSKMAP ID ${MAP_ID} to global bpffs: ${XSK_MAP_PATH}"
sudo bpftool map pin id "${MAP_ID}" "${XSK_MAP_PATH}"

# 3. Verify Visibility inside the Network Namespace via Native nsenter
echo "[+] Validating control-plane map descriptor visibility across netns..."
if ! sudo nsenter --net=/run/netns/${NS_NAME} ls -la "${XSK_MAP_PATH}" &>/dev/null; then
    echo "[-] CRITICAL FAULT: Map path invisible within namespace target."
    exit 1
fi
echo "[+] Invariant Path verified: ${XSK_MAP_PATH} is globally stable."

# 4. Refresh Interface IP Topology
echo "[+] Refreshing link layer interfaces..."
sudo ip addr add 10.0.0.1/24 dev veth_peer 2>/dev/null || true
sudo ip link set dev veth_peer up

sudo ip netns exec "${NS_NAME}" ip addr add 10.0.0.2/24 dev veth_ingress 2>/dev/null || true
sudo ip netns exec "${NS_NAME}" ip link set dev veth_ingress up

# 5. Boot the Cache-Aligned Consumer Daemon
echo "[+] Spawning Sophia Telemetry Consumer. Launching traffic loop..."
echo "[!] Launching flood traffic manually via another window using:"
echo "    sudo ping -f -c 2000 -I veth_peer 10.0.0.2"
echo "--------------------------------------------------------"

sudo nsenter --net=/run/netns/${NS_NAME} ./xsk_consumer
