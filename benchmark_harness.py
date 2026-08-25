#!/usr/bin/env python3
"""
High-Speed Ingress Stresser & Transit Latency Auditor
Generates sustained UDP traffic and captures latency metrics.
"""
import socket
import time
import sys
import os

TARGET_IP = "127.0.0.1"
TARGET_PORT = 9999
PACKET_COUNT = 500000
PAYLOAD_SIZE = 64

def run_benchmark():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = os.urandom(PAYLOAD_SIZE)
    
    print(f"[*] Sending {PACKET_COUNT} packets to {TARGET_IP}:{TARGET_PORT}...")
    start_time = time.perf_counter()

    for _ in range(PACKET_COUNT):
        sock.sendto(payload, (TARGET_IP, TARGET_PORT))

    total_time = time.perf_counter() - start_time
    rate = PACKET_COUNT / total_time
    print(f"[✓] Completed in {total_time:.3f}s | Throughput: {rate:,.0f} pkts/sec")

if __name__ == '__main__':
    run_benchmark()
