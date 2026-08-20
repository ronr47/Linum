#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum
sudo pkill -9 -f qemu-system-x86_64 2>/dev/null || true

echo "[*] Launching exokernel with QMP monitor to capture rendering..."
qemu-system-x86_64 \
    -drive format=raw,file=beast_disk.bin,file.locking=off,readonly=on \
    -vga std \
    -display none \
    -m 256M \
    -qmp unix:/tmp/qmp-sock,server,nowait &

QEMU_PID=$!
sleep 1.2

# Send screendump command via QMP socket
echo '{"execute": "qmp_capabilities"}{"execute": "screendump", "arguments": {"filename": "/tmp/beast_screen.ppm"}}' | socat - UNIX-CONNECT:/tmp/qmp-sock >/dev/null 2>&1 || true

# Kill QEMU instance
kill -9 $QEMU_PID 2>/dev/null || true
rm -f /tmp/qmp-sock

if [ -f /tmp/beast_screen.ppm ]; then
    echo "[✔] Framebuffer dumped to /tmp/beast_screen.ppm"
    # Convert to PNG if imagemagick/ffmpeg is present
    if command -v convert >/dev/null 2>&1; then
        convert /tmp/beast_screen.ppm beast_screen.png
        echo "[✔] Converted to ./beast_screen.png"
    elif command -v ffmpeg >/dev/null 2>&1; then
        ffmpeg -y -i /tmp/beast_screen.ppm beast_screen.png >/dev/null 2>&1
        echo "[✔] Converted to ./beast_screen.png"
    fi
    ls -lh /tmp/beast_screen.ppm beast_screen.png 2>/dev/null || true
else
    echo "[!] Screendump failed (check if socat is installed: sudo apt install socat)"
fi
