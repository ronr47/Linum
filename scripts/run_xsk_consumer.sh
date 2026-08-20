#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
NETNS="linum_sandbox"
IFACE="veth_ingress"
QUEUE="0"
CONSUMER="${ROOT}/build/xsk_consumer"

[[ -x "${CONSUMER}" ]] || {
    printf '%s\n' "ERROR: missing executable: ${CONSUMER}" >&2
    exit 1
}

[[ -e "/run/netns/${NETNS}" ]] || {
    printf '%s\n' "ERROR: missing network namespace: ${NETNS}" >&2
    exit 1
}

[[ -e "/sys/fs/bpf/linum_xsk_map" ]] || {
    printf '%s\n' 'ERROR: canonical XSKMAP pin missing' >&2
    exit 1
}

printf '%s\n' '=== LINUM AF_XDP CONSUMER ==='
printf 'Network namespace: %s\n' "${NETNS}"
printf 'Interface:         %s\n' "${IFACE}"
printf 'Queue:             %s\n' "${QUEUE}"
printf 'Mount namespace:   host'
printf '\n'

exec nsenter \
    --net="/run/netns/${NETNS}" \
    "${CONSUMER}" \
    "${IFACE}" \
    "${QUEUE}"
