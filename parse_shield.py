#!/usr/bin/env python3
import json
import subprocess
import socket
import struct

try:
    map_id = "24"
    
    # Extract map dump in clean JSON format
    raw_json = subprocess.check_output(["sudo", "bpftool", "map", "dump", "id", map_id, "-j"], text=True)
    entries = json.loads(raw_json)
    
    print("\n" + "="*80)
    print(f" LINUM SHIELD PROTOCOL ANALYZER - PRODUCTION MATRIX ENGINE (MAP ID: {map_id})")
    print("="*80)
    print(f"{'Source IP Address':<18} | {'Total Pkts':<10} | {'TCP Pkts':<10} | {'UDP Pkts':<10} | {'Blocked Pkts':<12}")
    print("-"*80)
    
    for entry in entries:
        # 1. Parse raw keys as Big Endian to prevent double-reversing the host stream
        key_list = entry['key']
        key_ints = [int(t, 16) if isinstance(t, str) else int(t) for t in key_list]
        
        # Build raw string output matching network byte order directly
        ip_addr = ".".join(str(b) for b in key_ints)
        
        # 2. Extract value byte array payload
        val_list = entry['value']
        val_bytes = bytes([int(t, 16) if isinstance(t, str) else int(t) for t in val_list])
        
        # Struct unpack padding correction: Unpack four 64-bit integers (__u64)
        if len(val_bytes) >= 32:
            total_pkts, tcp_pkts, udp_pkts, blocked_pkts = struct.unpack('<QQQQ', val_bytes[:32])
        else:
            # Fallback layout calculation if the compiler optimized the structure sizes down
            total_pkts = int.from_repr(val_bytes, byteorder='little') if val_bytes else 0
            tcp_pkts, udp_pkts, blocked_pkts = 0, 0, 0
            
        print(f"{ip_addr:<18} | {total_pkts:<10} | {tcp_pkts:<10} | {udp_pkts:<10} | {blocked_pkts:<12}")
    print("="*80 + "\n")

except Exception as e:
    print(f"[-] Telemetry Parser Error: {e}")
