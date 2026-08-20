#!/usr/bin/env bash
set -euo pipefail

NETNS="linum_sandbox"
BPF="/sys/fs/bpf"
HOST_BPF="/proc/1/root/sys/fs/bpf"

printf '%s\n' '=== LINUM BPF MOUNT REPAIR ==='

printf '%s\n' '=== HOST BPF FILESYSTEM ==='
findmnt "${BPF}"
stat -fc 'HOST fs=%d type=%T' "${BPF}"

printf '%s\n' '=== HOST XSKMAP PIN ==='
/usr/sbin/bpftool map show pinned \
    "${BPF}/linum_xsk_map"

printf '%s\n' '=== HOST PROGRAM PIN ==='
/usr/sbin/bpftool prog show pinned \
    "${BPF}/linum_xdp_prog"

printf '%s\n' '=== CURRENT NETNS BPF FILESYSTEM ==='
ip netns exec "${NETNS}" \
    findmnt "${BPF}" || true

ip netns exec "${NETNS}" \
    stat -fc 'NETNS fs=%d type=%T' "${BPF}"

printf '%s\n' '=== REMOVE NAMESPACE BPF MOUNT ==='
ip netns exec "${NETNS}" \
    umount "${BPF}" 2>/dev/null || true

printf '%s\n' '=== ENSURE TARGET EXISTS ==='
ip netns exec "${NETNS}" \
    mkdir -p "${BPF}"

printf '%s\n' '=== BIND HOST BPF SUPERBLOCK INTO NETNS ==='
ip netns exec "${NETNS}" \
    mount --bind "${HOST_BPF}" "${BPF}"

printf '%s\n' '=== VERIFY NETNS MOUNT ==='
ip netns exec "${NETNS}" \
    findmnt "${BPF}"

printf '%s\n' '=== VERIFY SUPERBLOCK IDENTITY ==='

printf '%s\n' 'HOST:'
stat -fc 'fs=%d type=%T' "${BPF}"

printf '%s\n' 'NETNS:'
ip netns exec "${NETNS}" \
    stat -fc 'fs=%d type=%T' "${BPF}"

printf '%s\n' '=== VERIFY MAP FROM NETNS ==='
ip netns exec "${NETNS}" \
    /usr/sbin/bpftool map show pinned \
    "${BPF}/linum_xsk_map"

printf '%s\n' '=== VERIFY PROGRAM FROM NETNS ==='
ip netns exec "${NETNS}" \
    /usr/sbin/bpftool prog show pinned \
    "${BPF}/linum_xdp_prog"

printf '%s\n' '=== VERIFY OBJECT PATH ==='
ip netns exec "${NETNS}" \
    test -e "${BPF}/linum_xsk_map"

printf '%s\n' 'NETNS_XSKMAP_VISIBLE=1'

printf '%s\n' '=== REPAIR COMPLETE ==='
