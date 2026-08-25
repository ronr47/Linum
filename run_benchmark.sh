#!/usr/bin/env bash
set -e

echo "=== [1/3] Compiling Gateway V6 & Traffic Generator V3 ==="
gcc -O3 -std=gnu11 -Wall -Wextra -pthread gateway_core_v6.c -o gateway_core_v6
gcc -O3 -std=gnu11 -Wall -Wextra -pthread traffic_gen_v3.c -o traffic_gen_v3

echo "=== [2/3] Starting Gateway V6 in Background ==="
./gateway_core_v6 9999 &
GW_PID=$!
sleep 1

echo "=== [3/3] Firing 1,000,000 Packets Load ==="
./traffic_gen_v3 1000000 9999 -1 127.0.0.1

echo "=== Stopping Gateway & Printing Telemetry Report ==="
kill -SIGINT "$GW_PID"
wait "$GW_PID"
