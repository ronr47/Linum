import subprocess
import time
import os

disk_image = "/home/ron/linum/os_unified_disk.bin"
log_file = "/tmp/qemu_fiber_serial.log"

if os.path.exists(log_file):
    os.remove(log_file)

qemu_cmd = [
    "qemu-system-x86_64",
    "-drive", f"file={disk_image},format=raw,if=ide,snapshot=on",
    "-serial", f"file:{log_file}",
    "-display", "none",
    "-m", "256M"
]

print("[*] Booting 3-Fiber Long Mode Exokernel (snapshot mode)...")
proc = subprocess.Popen(qemu_cmd)

try:
    time.sleep(2.0)
finally:
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

print("\n============================================================")
print(" 📜 SERIAL COM1 OUTPUT: 3-FIBER COOPERATIVE LOGS")
print("============================================================")
if os.path.exists(log_file):
    with open(log_file, "r", errors="ignore") as f:
        print(f.read())
else:
    print("[-] No serial log captured.")
