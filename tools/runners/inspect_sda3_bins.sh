#!/usr/bin/env bash
set -euo pipefail

sudo mkdir -p /mnt/sda3_audit
sudo mount -o ro /dev/sda3 /mnt/sda3_audit

OUT_DIR="/home/ron/linum/carved_sda3"
mkdir -p "$OUT_DIR"

echo "============================================================"
echo " 📦 FINGERPRINTING SDA3 BARE-METAL BINARIES"
echo "============================================================"

for f in boot.bin model.bin trinity_core.bin raw.bin test.bin; do
    FPATH="/mnt/sda3_audit/home/ronronalds/$f"
    if [ -f "$FPATH" ]; then
        cp "$FPATH" "$OUT_DIR/$f"
        SIZE=$(stat -c%s "$OUT_DIR/$f")
        FILE_TYPE=$(file -b "$OUT_DIR/$f")
        echo -e "\n[★] $f (${SIZE} bytes)"
        echo "    ▶ File Type: $FILE_TYPE"
        
        # Display printable strings / identifiers
        STRS=$(strings -a "$OUT_DIR/$f" | grep -v '^[._]' | head -n 6 | tr '\n' ', ' || true)
        if [ -n "$STRS" ]; then
            echo "    ▶ Strings  : $STRS"
        fi
        
        # Check for Multiboot/ELF headers
        python3 -c "
with open('$OUT_DIR/$f', 'rb') as fp:
    header = fp.read(64)
    if header.startswith(b'\x7fELF'):
        print('    ▶ Architecture: ELF Binary')
    elif b'\x02\xb0\xad\x1b' in header:
        print('    ▶ Architecture: Multiboot Kernel Header')
    elif header.endswith(b'\x55\xaa'):
        print('    ▶ Architecture: MBR / Boot Sector (0xAA55 Signature)')
"
    fi
done

sudo umount /mnt/sda3_audit
sudo rmdir /mnt/sda3_audit
