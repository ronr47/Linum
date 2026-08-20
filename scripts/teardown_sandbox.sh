#!/usr/bin/env bash
set -u

NS_NAME="linum_sandbox"
VETH_PEER="veth_peer"

echo "=== Deconstructing Linum XDP sandbox ==="

if ip netns list | awk '{print $1}' | grep -qx "${NS_NAME}"; then
    echo "[+] Detaching XDP"
    ip netns exec "${NS_NAME}" \
        ip link set dev veth_ingress xdpdrv off 2>/dev/null || true
fi

if ip link show dev "${VETH_PEER}" >/dev/null 2>&1; then
    echo "[+] Removing veth pair"
    ip link del "${VETH_PEER}" 2>/dev/null || true
fi

if ip netns list | awk '{print $1}' | grep -qx "${NS_NAME}"; then
    echo "[+] Removing namespace"
    ip netns del "${NS_NAME}" 2>/dev/null || true
fi

echo "[+] Sandbox teardown complete."
