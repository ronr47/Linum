#!/usr/bin/env bash
set -e

mkdir -p ~/.local/bin
export PATH="${HOME}/local/bin:${PATH}"

echo "[*] Compiling lightweight QBE IL backend from source..."
if [ ! -f "${HOME}/.local/bin/qbe" ]; then
    git clone --depth=1 git://c9x.me/qbe.git /tmp/qbe 2>/dev/null || true
    if [ -d "/tmp/qbe" ]; then
        make -C /tmp/qbe -j2
        cp /tmp/qbe/obj/qbe ~/.local/bin/
        rm -rf /tmp/qbe
        echo "    └─ [✔] QBE compiled and placed in ~/.local/bin/qbe"
    fi
fi

echo "[*] Auditing full toolchain..."
~/.local/bin/qbe -h 2>/dev/null | head -n 1 || true
