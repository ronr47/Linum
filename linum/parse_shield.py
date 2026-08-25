#!/usr/bin/env python3
import json
import subprocess
import socket
import struct

def parse_hex_token(token):
    # Normalize string inputs to raw integers (handles "0xca", "ca", or native ints)
    if isinstance(token, str):
        return int(token, 16)
    return int(token)

try:
    map_id = "24"
    
    # Extract map dump in clean JSON format
    raw_json = subprocess.check_output(["sudo", "bpftool", "map", "dump", "id", map_id, "-j"], text=True)
    entries = json.loads(raw_json)
    
    print("\n" + "="*80)
    print(f" LINUM ADAPTIVE SHIELD PROTOCOL ANALYZER - METRICS ENGINE (MAP ID: {map_id})")
    print("="*80)
    print(f"{'Source IP Address':<18} | {'Traffic Signal Payload Metrics / Counter State':<45}")
    print("-"*80)
    
    for entry in entries:
        # 1. Normalize and extract the IP key tracking elements safely
        key_list = entry['key']
        key_ints = [parse_hex_token(t) for t in key_list]
        
        # Reconstruct Little Endian byte structure
        key_raw = int("".join([f"{b:02x}" for b in reversed(key_ints)]), 16)
        ip_addr = socket.inet_ntoa(struct.pack('<I', key_raw))
        
        # 2. Normalize and extract value payloads
        val_list = entry['value']
        val_ints = [parse_hex_token(t) for t in val_list]
        
        # If the map fields packed down tightly, decode the base metric index counter
        hex_val = "".join([f"{b:02x}" for b in val_ints])
        int_val = int(hex_val, 16) if hex_val else 0
        
        print(f"{ip_addr:<18} | Traffic Counter Sequence Index: {int_val} packets captured")
    print("="*80 + "\n")

except Exception as e:
    print(f"[-] Telemetry Engine Parsing Error: {e}")
