#!/usr/bin/env python3
import socket
import time
import json
import urllib.request
import sys

OBD_HOST = "127.0.0.1"
OBD_PORT = 8888
SERVER_URL = "http://127.0.0.1:8080/telemetry"

def read_obd_response(sock, timeout=2.5):
    buf = ""
    start = time.time()
    while time.time() - start < timeout:
        try:
            chunk = sock.recv(64).decode('latin1', errors='ignore')
            if not chunk:
                time.sleep(0.01)
                continue
            buf += chunk
            if '>' in buf:
                return buf.replace('>', '').strip()
        except socket.timeout:
            break
        except Exception:
            break
    return buf.strip() if buf else None

def send_obd(sock, cmd):
    sock.send((cmd.strip() + "\r").encode('ascii'))
    return read_obd_response(sock)

def parse_rpm(res):
    try:
        parts = res.split()
        if "41" in parts:
            i = parts.index("41")
            if parts[i+1] == "0C":
                return ((int(parts[i+2], 16) * 256) + int(parts[i+3], 16)) / 4.0
    except Exception:
        pass
    return 0.0

def parse_speed(res):
    try:
        parts = res.split()
        if "41" in parts:
            i = parts.index("41")
            if parts[i+1] == "0D":
                return int(parts[i+2], 16)
    except Exception:
        pass
    return 0

def post_telemetry(payload):
    try:
        req = urllib.request.Request(
            SERVER_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=0.5)
    except Exception:
        pass

def main():
    print("[*] Linum Master Telemetry Router Initializing...")
    print(f"[*] Attaching to OBD Bridge at {OBD_HOST}:{OBD_PORT}...")
    try:
        obd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        obd.settimeout(3.0)
        obd.connect((OBD_HOST, OBD_PORT))
        print("[+] Physical OBD Link verified.")
    except Exception as e:
        print(f"[-] OBD transport unavailable: {e}")
        print("[!] Ensure the Bluetooth TCP server is running on port 8888.")
        sys.exit(1)

    send_obd(obd, "ATE0")
    send_obd(obd, "ATSP0")
    v_raw = send_obd(obd, "ATRV")
    voltage = v_raw.replace("\r", " ").strip() if v_raw else "N/A"

    print("[*] Telemetry stream active. Routing to Linum Command Server...")
    try:
        while True:
            rpm = parse_rpm(send_obd(obd, "010C") or "")
            spd = parse_speed(send_obd(obd, "010D") or "")

            telemetry = {
                "engine_rpm": rpm,
                "vehicle_speed_kmh": spd,
                "battery_voltage": voltage,
                "status": "ONLINE",
                "stamp": "R2_LINUM"
            }
            post_telemetry(telemetry)
            print(f"\r[TELEMETRY] RPM: {rpm:<6.1f} | Speed: {spd:<3} km/h | Bus: {voltage}", end="", flush=True)
            time.sleep(0.04)
    except KeyboardInterrupt:
        print("\n[*] Bridge stopped.")
    finally:
        obd.close()

if __name__ == "__main__":
    main()
