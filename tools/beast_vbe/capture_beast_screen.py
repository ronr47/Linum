import socket
import time
import os
import subprocess
import signal

SOCK_PATH = "/tmp/qemu-hmp.sock"
PPM_PATH = "/tmp/beast_screen.ppm"
PNG_PATH = "beast_screen.png"

# 1. Clean previous artifacts
for p in [SOCK_PATH, PPM_PATH]:
    if os.path.exists(p):
        try: os.remove(p)
        except OSError: pass

# 2. Launch QEMU with HMP unix socket & VGA std
qemu_cmd = [
    "qemu-system-x86_64",
    "-drive", "file=beast_disk.bin,format=raw,if=ide",
    "-vga", "std",
    "-display", "none",
    "-m", "256M",
    "-monitor", f"unix:{SOCK_PATH},server,nowait"
]

print("[*] Launching exokernel with HMP monitor...")
proc = subprocess.Popen(qemu_cmd)

try:
    # Wait for socket initialization and frame rendering
    time.sleep(1.5)
    
    # 3. Connect to HMP socket and trigger screendump
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK_PATH)
    time.sleep(0.2)
    s.recv(1024) # flush prompt
    
    cmd = f"screendump {PPM_PATH}\n"
    s.sendall(cmd.encode("utf-8"))
    time.sleep(0.5)
    s.close()
    print(f"[✔] screendump command dispatched to {PPM_PATH}")

finally:
    # 4. Clean shutdown
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
    if os.path.exists(SOCK_PATH):
        try: os.remove(SOCK_PATH)
        except OSError: pass

# 5. Convert PPM to PNG if tools are present
if os.path.exists(PPM_PATH):
    size = os.path.getsize(PPM_PATH)
    print(f"[✔] Framebuffer PPM generated ({size} bytes)")
    
    conv = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
    if conv.returncode == 0:
        subprocess.run(["ffmpeg", "-y", "-i", PPM_PATH, PNG_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[✔] Rendered PNG screenshot: {PNG_PATH}")
    else:
        conv2 = subprocess.run(["which", "convert"], capture_output=True, text=True)
        if conv2.returncode == 0:
            subprocess.run(["convert", PPM_PATH, PNG_PATH])
            print(f"[✔] Rendered PNG screenshot: {PNG_PATH}")
else:
    print("[!] PPM screendump file was not produced.")
