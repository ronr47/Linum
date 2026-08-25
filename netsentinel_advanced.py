#!/usr/bin/env python3
# NetSentinel v2.0 - Advanced Multi-Threaded Network Audit & Event Correlator
# Optimizations: Parallel task workers, structural XML parsing, native timeout abstraction, accurate log validation.

import subprocess
import json
import os
import tempfile
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

# Core configuration parameters
SUBNET = "192.168.1.0/24"
SNAP_LENGTH = 10
OUTPUT_FILE = "netsentinel_advanced_report.json"

def run_command(cmd, timeout_duration=120):
    """Executes a system process explicitly via array mapping without shell overhead."""
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_duration
        )
        return res.stdout.strip(), res.stderr.strip(), res.returncode
    except subprocess.TimeoutExpired:
        return "", f"EXEC_TIMEOUT: Exceeded {timeout_duration}s limits.", 124
    except Exception as err:
        return "", f"EXEC_FAILED: {str(err)}", 1

def get_nmap_scan():
    """Executes structural subnet profiling and extracts network geometry using tree generation."""
    print(f"[*] Dispatching Nmap execution engine across {SUBNET}...")
    cmd = ["nmap", "-sT", "-O", "--open", "-oX", "-", SUBNET]
    stdout, stderr, rc = run_command(cmd, timeout_duration=180)
    
    if rc != 0:
        return {"error": stderr}
        
    hosts = []
    try:
        root = ET.fromstring(stdout)
        for host_node in root.findall('host'):
            # Address resolution
            ip_addr = "Unknown"
            addr_elem = host_node.find("./address[@addrtype='ipv4']")
            if addr_elem is not None:
                ip_addr = addr_elem.get('addr')
                
            # OS classification matrix
            os_match = host_node.find("./os/osmatch")
            os_fingerprint = os_match.get('name') if os_match is not None else "Unidentified"
            
            # Extract port tables
            ports_mapped = []
            for port in host_node.findall("./ports/port"):
                p_id = port.get('portid')
                state_elem = port.find('state')
                
                if state_elem is not None and state_elem.get('state') == 'open':
                    svc_elem = port.find('service')
                    svc_name = svc_elem.get('name') if svc_elem is not None else "unassigned"
                    ports_mapped.append({"port": int(p_id), "service": svc_name})
                    
            hosts.append({
                "ip": ip_addr,
                "os": os_fingerprint,
                "ports": ports_mapped
            })
    except Exception as ex:
        return {"error": f"TREE_PARSING_EXCEPTION: {str(ex)}", "raw_payload": stdout}
        
    return {"hosts": hosts}

def get_tcpdump_sniff():
    """Captures interface frames safely via the system timeout utility layer."""
    print(f"[*] Opening raw capture interface for {SNAP_LENGTH}s...")
    
    fd, path = tempfile.mkstemp(suffix=".pcap")
    os.close(fd)
    
    # Prefixing the layout with system native timeout parameters
    cmd = ["timeout", str(SNAP_LENGTH), "tcpdump", "-i", "any", "-w", path, "-c", "2000"]
    stdout, stderr, rc = run_command(cmd, timeout_duration=SNAP_LENGTH + 5)
    
    # Status code 124 verifies expected loop breaks by the timeout engine
    if rc != 0 and rc != 124:
        return {"error": stderr}
        
    sz = os.path.getsize(path) if os.path.exists(path) else 0
    metrics = {"file_target": path, "size_bytes": sz}
    
    # Layer protocol metrics using tshark engine structures if online
    if sz > 24:
        ts_cmd = ["tshark", "-r", path, "-q", "-z", "io,phs"]
        ts_out, _, ts_rc = run_command(ts_cmd)
        if ts_rc == 0:
            metrics["protocol_hierarchy"] = ts_out.split('\n')
            
    return {"metrics": metrics}

def get_lynis_audit():
    """Monitors the local operating system surface layout for vulnerable conditions."""
    print("[*] Initiating Lynis hardening target scan...")
    cmd = ["lynis", "audit", "system", "--quick", "--auditor", "NetSentinel_Engine"]
    stdout, stderr, rc = run_command(cmd, timeout_duration=300)
    
    records = []
    # Lynis maps state metrics via text markers regardless of return definitions
    for line in stdout.split('\n'):
        if any(marker in line for marker in ["WARNING", "Suggestion", "Hardening index"]):
            records.append(line.strip())
            
    return {"findings": records}

def correlate_orchestration(nmap, tcpdump, lynis):
    """Parses structural arrays across distinct system namespaces to yield true vulnerabilities."""
    print("[*] Processing analytics across runtime matrices...")
    high_risk_vectors = []
    anomalous_activity = []
    
    # 1. Evaluate cross-network architecture vectors (Insecure cleartext interfaces)
    hosts_list = nmap.get("hosts", [])
    insecure_ports = {21: "FTP", 23: "Telnet", 80: "HTTP", 445: "SMB/Plain"}
    
    for device in hosts_list:
        for socket in device.get("ports", []):
            p_num = socket["port"]
            if p_num in insecure_ports:
                high_risk_vectors.append({
                    "target": f"{device['ip']}:{p_num}",
                    "component": insecure_ports[p_num],
                    "vector": "Unencrypted Cleartext Data Communication Transmission"
                })
                
    # 2. Correlate local interface capture volume bounds
    io_weight = tcpdump.get("metrics", {}).get("size_bytes", 0)
    if io_weight > 5000000:  # 5 Megabytes threshold limit validation
        anomalous_activity.append(f"HIGH_VOLUME_CAPTURE: Broadcast traffic overload verified ({io_weight} bytes).")
        
    # 3. Aggregate internal operating system configurations
    issues_logged = len(lynis.get("findings", []))
    
    return {
        "high_risk_vectors": high_risk_vectors,
        "anomalous_activity": anomalous_activity,
        "metrics_summary": {
            "discovered_subnet_hosts": len(hosts_list),
            "local_host_hardening_alerts": issues_logged,
            "monitored_pcap_bytes": io_weight
        }
    }

def main():
    print("="*65)
    print(" NETSENTINEL CORE v2.0 - ASYNCHRONOUS AUDIT EXECUTION ENGINE")
    print("="*65)
    
    if os.getuid() != 0:
        print("[!] FATAL: Operating thread requires root privileges (cap_net_raw execution missing).")
        return

    start_timestamp = time.time()
    
    # Asynchronous thread execution mapping across disjoint system dependencies
    with ThreadPoolExecutor(max_workers=3) as executor:
        nmap_future = executor.submit(get_nmap_scan)
        tcpdump_future = executor.submit(get_tcpdump_sniff)
        lynis_future = executor.submit(get_lynis_audit)
        
        nmap_res = nmap_future.result()
        tcpdump_res = tcpdump_future.result()
        lynis_res = lynis_future.result()
        
    analysis = correlate_orchestration(nmap_res, tcpdump_res, lynis_res)
    
    report_structure = {
        "metadata": {
            "schema_version": "2.0",
            "epoch_timestamp": int(time.time()),
            "subnet_target": SUBNET
        },
        "correlation_matrix": analysis,
        "raw_engine_outputs": {
            "nmap": nmap_res,
            "tcpdump": tcpdump_res,
            "lynis": lynis_res
        }
    }
    
    with open(OUTPUT_FILE, 'w') as stream:
        json.dump(report_structure, stream, indent=4, default=str)
        
    print("="*65)
    print(f"[*] PIPELINE TERMINATED SUCCESSFULLY IN {time.time() - start_timestamp:.2f} SECONDS")
    print(f"[*] OUTPUT SUMMARY WRITTEN DIRECTLY TO FILE TARGET: {OUTPUT_FILE}")
    print("="*65)
    
    if analysis["high_risk_vectors"]:
        print("\n[⚠️ ] CRITICAL INTERACTION VECTORS ENCOUNTERED:")
        for vulnerability in analysis["high_risk_vectors"]:
            print(f"  -> {vulnerability['target']} | {vulnerability['component']} -> {vulnerability['vector']}")
            
    if analysis["anomalous_activity"]:
        print("\n[⚠️ ] NETWORK INFRASTRUCTURE ANOMALIES:")
        for anomaly in analysis["anomalous_activity"]:
            print(f"  -> {anomaly}")

if __name__ == "__main__":
    main()
