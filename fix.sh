```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OBJ="${ROOT}/build/xdp_prog.o"

BPF_ROOT="/sys/fs/bpf"
PROG_PIN="${BPF_ROOT}/linum_xdp_prog"
XSK_PIN="${BPF_ROOT}/linum_xsk_map"
TELEMETRY_PIN="${BPF_ROOT}/linum_telemetry_map"

NETNS="linum_sandbox"
IFACE="veth_ingress"

printf '%s\n' '=== CLEAN OLD LINUM OBJECTS ==='

sudo rm -f \
    "${PROG_PIN}" \
    "${XSK_PIN}" \
    "${TELEMETRY_PIN}"

printf '%s\n' '=== VERIFY BPF FILESYSTEM ==='

sudo findmnt "${BPF_ROOT}"

test -f "${OBJ}" || {
    printf '%s\n' "ERROR: missing ${OBJ}" >&2
    exit 1
}

printf '%s\n' '=== LOAD LINUM XDP OBJECT ==='

sudo /usr/sbin/bpftool prog load \
    "${OBJ}" \
    "${PROG_PIN}" \
    type xdp \
    pinmaps "${BPF_ROOT}"

printf '%s\n' '=== VERIFY PROGRAM PIN ==='

sudo test -e "${PROG_PIN}"

sudo /usr/sbin/bpftool prog show pinned \
    "${PROG_PIN}"

printf '%s\n' '=== DISCOVER GENERATED MAPS ==='

sudo /usr/sbin/bpftool map show | \
    grep -E 'telemetry_map|xsks_map'

printf '%s\n' '=== DISCOVER EXACT MAP IDS ==='

XSKMAP_ID="$(
    sudo /usr/sbin/bpftool map show |
    awk '$2 == "xskmap" && $3 == "name" && $4 == "xsks_map" { gsub(":", "", $1); print $1; exit }'
)"

TELEMETRY_MAP_ID="$(
    sudo /usr/sbin/bpftool map show |
    awk '$2 == "hash" && $3 == "name" && $4 == "telemetry_map" { gsub(":", "", $1); print $1; exit }'
)"

test -n "${XSKMAP_ID}" || {
    printf '%s\n' 'ERROR: generated xsks_map not found' >&2
    exit 1
}

test -n "${TELEMETRY_MAP_ID}" || {
    printf '%s\n' 'ERROR: generated telemetry_map not found' >&2
    exit 1
}

printf 'XSKMAP_ID=%s\n' "${XSKMAP_ID}"
printf 'TELEMETRY_MAP_ID=%s\n' "${TELEMETRY_MAP_ID}"

printf '%s\n' '=== PIN GENERATED MAPS EXPLICITLY ==='

sudo /usr/sbin/bpftool map pin \
    id "${XSKMAP_ID}" \
    "${XSK_PIN}"

sudo /usr/sbin/bpftool map pin \
    id "${TELEMETRY_MAP_ID}" \
    "${TELEMETRY_PIN}"

printf '%s\n' '=== VERIFY PROGRAM → MAP RELATIONSHIP ==='

sudo /usr/sbin/bpftool prog show pinned \
    "${PROG_PIN}"

printf '%s\n' '=== VERIFY XSKMAP PIN ==='

sudo /usr/sbin/bpftool map show pinned \
    "${XSK_PIN}"

printf '%s\n' '=== VERIFY TELEMETRY MAP PIN ==='

sudo /usr/sbin/bpftool map show pinned \
    "${TELEMETRY_PIN}"

printf '%s\n' '=== VERIFY ALL PINNED OBJECTS ==='

sudo ls -lh \
    "${PROG_PIN}" \
    "${XSK_PIN}" \
    "${TELEMETRY_PIN}"

printf '%s\n' '=== ATTACH PINNED PROGRAM ==='

sudo ip netns exec "${NETNS}" \
    ip link set dev "${IFACE}" \
    xdp pinned "${PROG_PIN}"

printf '%s\n' '=== VERIFY XDP ATTACHMENT ==='

sudo ip netns exec "${NETNS}" \
    ip -details link show dev "${IFACE}"

printf '%s\n' '=== VERIFY XDP PROGRAM ==='

sudo /usr/sbin/bpftool net show

printf '%s\n' '=== FINAL PROGRAM STATE ==='

sudo /usr/sbin/bpftool prog show pinned \
    "${PROG_PIN}"

printf '%s\n' '=== FINAL XSKMAP STATE ==='

sudo /usr/sbin/bpftool map show pinned \
    "${XSK_PIN}"

printf '%s\n' '=== FINAL TELEMETRY STATE ==='

sudo /usr/sbin/bpftool map show pinned \
    "${TELEMETRY_PIN}"

printf '%s\n' '=== LINUM XDP DEPLOYMENT PASS ==='
```
