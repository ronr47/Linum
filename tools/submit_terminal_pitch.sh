#!/usr/bin/env bash
set -euo pipefail

PITCH_TITLE="How to Build a High-Performance eBPF Network Monitor in Rust Using Aya and Linux XDP"
AUTHOR_NAME="Ron"
AUTHOR_EMAIL="tatulatu700@gmail.com"
PORTFOLIO="https://github.com/ronr47/Linum"

# Construct JSON payload
cat << JSON_PAYLOAD > pitch_payload.json
{
  "author": "${AUTHOR_NAME}",
  "email": "${AUTHOR_EMAIL}",
  "portfolio": "${PORTFOLIO}",
  "title": "${PITCH_TITLE}",
  "summary": "Step-by-step production guide to compiling and deploying low-overhead eBPF packet monitors in pure Rust using Aya, hooked via XDP interfaces.",
  "outline": [
    "1. Kernel-Bypass Networking Concepts with Aya & eBPF",
    "2. Environment & Toolchain Setup (bpf-linker, Rust nightly)",
    "3. Writing the Kernel-Space XDP Packet Filter",
    "4. Building the User-Space Daemon and Memory Ring Buffers",
    "5. Live Throughput Benchmarks and Resource Teardown"
  ]
}
JSON_PAYLOAD

echo "[✔] Pitch payload generated at pitch_payload.json"

# Print formatted summary to terminal
cat pitch_payload.json | python3 -m json.tool
