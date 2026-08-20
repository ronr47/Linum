import subprocess

disk_image = "/home/ron/linum/os_unified_disk.bin"

qemu_cmd = [
    "qemu-system-x86_64",
    "-drive", f"file={disk_image},format=raw,if=ide,snapshot=on",
    "-device", "isa-debug-exit,iobase=0x501,iosize=0x02",
    "-serial", "stdio",
    "-display", "none",
    "-m", "256M"
]

print("[*] Booting 3-Fiber Long Mode Exokernel in QEMU...")
proc = subprocess.run(
    qemu_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    timeout=5
)

print("\n============================================================")
print(" 📜 SERIAL COM1 OUTPUT: 3-FIBER COOPERATIVE LOGS")
print("============================================================")
if proc.stdout.strip():
    print(proc.stdout)
else:
    print("[-] No serial output captured.")
    if proc.stderr.strip():
        print(f"[!] QEMU stderr: {proc.stderr}")
