#!/usr/bin/env bash
set -euo pipefail

NS_NAME="linum_sandbox"
VETH_PEER="veth_peer"
VETH_INGRESS="veth_ingress"
XDP_OBJ="$PWD/xdp_prog.o"
XDP_SEC="xdp"
BPFTOOL="/usr/sbin/bpftool"

echo "=== Initializing Linum XDP sandbox ==="

if ip netns list | awk '{print $1}' | grep -qx "${NS_NAME}"; then
    echo "[+] Removing stale namespace: ${NS_NAME}"
    ip netns del "${NS_NAME}" || true
fi

if ip link show dev "${VETH_PEER}" >/dev/null 2>&1; then
    echo "[+] Removing stale veth: ${VETH_PEER}"
    ip link del "${VETH_PEER}" || true
fi

echo "[+] Creating namespace: ${NS_NAME}"
ip netns add "${NS_NAME}"

echo "[+] Creating veth pair"
ip link add "${VETH_PEER}" type veth peer name "${VETH_INGRESS}"

echo "[+] Moving ${VETH_INGRESS} into ${NS_NAME}"
ip link set "${VETH_INGRESS}" netns "${NS_NAME}"

echo "[+] Bringing host endpoint up"
ip link set "${VETH_PEER}" up

echo "[+] Bringing namespace endpoint up"
ip netns exec "${NS_NAME}" ip link set lo up
ip netns exec "${NS_NAME}" ip link set "${VETH_INGRESS}" up

echo "[+] Driver information"
ip netns exec "${NS_NAME}" ethtool -i "${VETH_INGRESS}" || true

echo "[+] Attaching NATIVE XDP"
ip netns exec "${NS_NAME}" \
    ip link set dev "${VETH_INGRESS}" \
    xdpgeneric obj "${XDP_OBJ}" sec "${XDP_SEC}"

echo
echo "=== Sandbox Verification ==="

echo "--- interface ---"
ip netns exec "${NS_NAME}" \
    ip -details link show dev "${VETH_INGRESS}"

echo "--- XDP attachment ---"
ip netns exec "${NS_NAME}" \
    "${BPFTOOL}" net show

echo "--- loaded XDP programs ---"
ip netns exec "${NS_NAME}" \
    "${BPFTOOL}" prog show type xdp

echo
echo "[+] Native XDP sandbox verified."
