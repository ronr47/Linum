import subprocess
import time
import socket
import os

cd = "/home/ron/linum"
os.chdir(cd)

SOCK_PATH = "/tmp/qemu-vbe-hmp.sock"
PPM_PATH = "/tmp/beast_vbe_full.ppm"

for p in [SOCK_PATH, PPM_PATH]:
    if os.path.exists(p):
        try: os.remove(p)
        except OSError: pass

cmd = [
    "qemu-system-x86_64",
    "-drive", "file=beast_vbe_disk.bin,format=raw,if=ide",
    "-vga", "std",
    "-display", "none",
    "-m", "256M",
    "-monitor", f"unix:{SOCK_PATH},server,nowait"
]

print("[*] Launching exokernel to complete all fiber rendering cycles...")
proc = subprocess.Popen(cmd)

try:
    # Give the cooperative fibers sufficient execution cycles
    time.sleep(3.5)
    
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK_PATH)
    time.sleep(0.2)
    s.recv(1024)
    s.sendall(f"screendump {PPM_PATH}\n".encode())
    time.sleep(0.5)
    s.close()
    print(f"[✔] Full canvas dumped to {PPM_PATH}")
finally:
    proc.terminate()
    try: proc.wait(timeout=2)
    except subprocess.TimeoutExpired: proc.kill()
    if os.path.exists(SOCK_PATH):
        try: os.remove(SOCK_PATH)
        except OSError: pass

if os.path.exists(PPM_PATH):
    with open(PPM_PATH, "rb") as f:
        f.readline(); f.readline(); f.readline()
        data = f.read()

    from collections import Counter
    pixels = [tuple(data[i:i+3]) for i in range(0, len(data), 3)]
    counts = Counter(pixels)

    print("\n============================================================")
    print(" 🎨 FULL FRAMEBUFFER SPECTRUM & GEOMETRY")
    print("============================================================")
    for (r, g, b), count in counts.most_common(10):
        pct = (count / len(pixels)) * 100
        print(f"  RGB({r:3d}, {g:3d}, {b:3d}) | HEX: #{r:02X}{g:02X}{b:02X} | Pixels: {count:7d} ({pct:5.2f}%)")
