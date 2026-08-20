#!/usr/bin/env bash
set -Eeuo pipefail

# XDP, AF_XDP, network namespaces, and BPF pinning require root.
# Elevate once so every operation below executes in one consistent privilege
# domain instead of mixing privileged and unprivileged namespace operations.
if (( EUID != 0 )); then
    exec sudo -- "$0" "$@"
fi

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BUILD="${ROOT}/build"

NETNS="linum_sandbox"
IFACE="veth_ingress"
QUEUE=0

BPF="/sys/fs/bpf"

XDP_SRC="${ROOT}/xdp_prog.c"
XSK_SRC="${ROOT}/xsk_consumer.c"

LINUM_TYPES="${BUILD}/linum_types.h"

XDP_OBJ="${BUILD}/xdp_prog.o"
XSK_BIN="${BUILD}/xsk_consumer"

PROG_PIN="${BPF}/linum_xdp_prog"
XSK_PIN="${BPF}/linum_xsk_map"
TELEMETRY_PIN="${BPF}/linum_telemetry_map"

BPFT="/usr/sbin/bpftool"

section() {
    printf '\n============================================================\n'
    printf ' %s\n' "$1"
    printf '============================================================\n'
}

die() {
    printf 'FATAL: %s\n' "$*" >&2
    exit 1
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 ||
        die "required command not found: $1"
}

section "LINUM XDP / AF_XDP FULL REBUILD"

section "0. SOURCE DEPENDENCY AUDIT"

[[ -f "$XDP_SRC" ]] ||
    die "missing XDP source: $XDP_SRC"

[[ -f "$XSK_SRC" ]] ||
    die "missing AF_XDP consumer source: $XSK_SRC"

[[ -f "$LINUM_TYPES" ]] ||
    die "missing generated header: $LINUM_TYPES"

printf 'ROOT:             %s\n' "$ROOT"
printf 'XDP SOURCE:       %s\n' "$XDP_SRC"
printf 'XSK SOURCE:       %s\n' "$XSK_SRC"
printf 'LINUM TYPES:      %s\n' "$LINUM_TYPES"
printf 'INCLUDE DIRECTORY: %s\n' "$BUILD"

section "1. VERIFY TOOLCHAIN"

require_cmd clang
require_cmd cc
require_cmd ip
require_cmd "$BPFT"

printf 'clang:    '
clang --version | head -n 1

printf 'cc:       '
cc --version | head -n 1

printf 'bpftool:  '
"$BPFT" version

section "2. VERIFY BPF FILESYSTEM"

[[ -d "$BPF" ]] ||
    die "BPF filesystem path does not exist: $BPF"

findmnt "$BPF" ||
    die "$BPF is not mounted"

[[ "$(findmnt -n -o FSTYPE "$BPF")" == "bpf" ]] ||
    die "$BPF is not a BPF filesystem"

section "3. VERIFY NETWORK NAMESPACE"

NS_HANDLE="/run/netns/${NETNS}"

[[ -e "$NS_HANDLE" ]] ||
    die "network namespace handle does not exist: $NS_HANDLE"

# Do not use `ip netns identify "$NETNS"` here.
# `ip netns identify` takes a PID and returns that PID's namespace name.
# For a named namespace, the persistent /run/netns handle plus an actual
# `ip netns exec` operation are the authoritative checks.

ip netns exec "$NETNS"     ip link show dev "$IFACE" >/dev/null 2>&1 ||
    die "interface $IFACE does not exist in namespace $NETNS"

printf 'namespace: %s\n' "$NETNS"
printf 'handle:    %s\n' "$NS_HANDLE"
printf 'interface: %s\n' "$IFACE"
printf 'queue:     %s\n' "$QUEUE"

section "4. STOP OLD CONSUMERS"

pkill -TERM -x xsk_consumer 2>/dev/null || true
sleep 1
pkill -KILL -x xsk_consumer 2>/dev/null || true

if pgrep -x xsk_consumer >/dev/null 2>&1; then
    die "stale xsk_consumer process remains"
fi

section "5. DETACH OLD XDP"

ip netns exec "$NETNS" \
    ip link set dev "$IFACE" xdp off 2>/dev/null || true

ip netns exec "$NETNS" \
    ip link set dev "$IFACE" xdpdrv off 2>/dev/null || true

ip netns exec "$NETNS" \
    ip link set dev "$IFACE" xdpgeneric off 2>/dev/null || true

section "6. REMOVE OLD PINS"

rm -f \
    "$PROG_PIN" \
    "$XSK_PIN" \
    "$TELEMETRY_PIN"

section "7. VERIFY OLD PINS ARE GONE"

[[ ! -e "$PROG_PIN" ]] ||
    die "old program pin still exists"

[[ ! -e "$XSK_PIN" ]] ||
    die "old XSK map pin still exists"

[[ ! -e "$TELEMETRY_PIN" ]] ||
    die "old telemetry map pin still exists"

section "8. BUILD XDP OBJECT"

clang \
    -O2 \
    -g \
    -target bpf \
    -D__TARGET_ARCH_x86 \
    -I/usr/include \
    -I/usr/include/x86_64-linux-gnu \
    -c "$XDP_SRC" \
    -o "$XDP_OBJ"

file "$XDP_OBJ"

section "9. BUILD AF_XDP CONSUMER"

cc \
    -O2 \
    -g \
    -Wall \
    -Wextra \
    -I"$BUILD" \
    "$XSK_SRC" \
    -o "$XSK_BIN" \
    -lxdp \
    -lbpf

file "$XSK_BIN"

section "10. LOAD XDP OBJECT"

"$BPFT" prog loadall \
    "$XDP_OBJ" \
    "$BUILD/xdp_prog"

section "11. DISCOVER LOADED BPF OBJECTS"

"$BPFT" prog show

section "12. PIN PROGRAM AND MAPS"

PROG_ID="$(
    "$BPFT" prog show |
    awk '
        /name xdp_prog / {
            gsub(":", "", $1)
            print $1
            exit
        }
    '
)"

[[ -n "$PROG_ID" ]] ||
    die "unable to locate loaded xdp_prog"

"$BPFT" prog pin id "$PROG_ID" "$PROG_PIN"

MAP_XSK_ID="$(
    "$BPFT" map show |
    awk '
        /xskmap/ && /name xsks_map/ {
            gsub(":", "", $1)
            print $1
            exit
        }
    '
)"

[[ -n "$MAP_XSK_ID" ]] ||
    die "unable to locate xsks_map"

"$BPFT" map pin id "$MAP_XSK_ID" "$XSK_PIN"

MAP_TELEMETRY_ID="$(
    "$BPFT" map show |
    awk '
        /name telemetry_map/ {
            gsub(":", "", $1)
            print $1
            exit
        }
    '
)"

[[ -n "$MAP_TELEMETRY_ID" ]] ||
    die "unable to locate telemetry_map"

"$BPFT" map pin id "$MAP_TELEMETRY_ID" "$TELEMETRY_PIN"

section "13. VERIFY PINS"

"$BPFT" prog show pinned "$PROG_PIN"
"$BPFT" map show pinned "$XSK_PIN"
"$BPFT" map show pinned "$TELEMETRY_PIN"

section "14. ATTACH XDP PROGRAM"

ip netns exec "$NETNS" \
    ip link set dev "$IFACE" \
    xdp pinned "$PROG_PIN"

section "15. VERIFY ATTACHMENT"

ip netns exec "$NETNS" \
    ip -details link show dev "$IFACE"

section "16. BPF NETWORK STATE"

"$BPFT" net show

section "17. VERIFY FINAL PINS"

"$BPFT" prog show pinned "$PROG_PIN"
"$BPFT" map show pinned "$XSK_PIN"
"$BPFT" map show pinned "$TELEMETRY_PIN"

section "18. FINAL STATE"

printf 'Namespace: %s\n' "$NETNS"
printf 'Interface: %s\n' "$IFACE"
printf 'Queue:     %s\n' "$QUEUE"

printf '\n=== PROGRAM ===\n'
"$BPFT" prog show pinned "$PROG_PIN"

printf '\n=== XSK MAP ===\n'
"$BPFT" map show pinned "$XSK_PIN"

printf '\n=== TELEMETRY MAP ===\n'
"$BPFT" map show pinned "$TELEMETRY_PIN"

printf '\n=== INTERFACE ===\n'
ip netns exec "$NETNS" \
    ip -details link show dev "$IFACE"

printf '\n============================================================\n'
printf ' LINUM XDP / AF_XDP REBUILD COMPLETE\n'
printf '============================================================\n'
