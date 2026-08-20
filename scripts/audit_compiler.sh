#!/usr/bin/env bash
set -euo pipefail

echo "=== [AUDIT 1: COMPILER PATH & VERSION TRACE] ==="
which gcc
gcc --version

echo -e "\n=== [AUDIT 2: HARDCODED SECURITY DEFAULTS] ==="
echo "Checking if your GCC binary automatically enforces PIE (Position Independent Executable),"
echo "Stack Protectors, or Read-Only Relocations (RELRO) by default:"
gcc -dumpspecs 2>/dev/null | grep -E -i 'fstack-protector|pie|relro' || echo "[Matrix Note]: GCC is using lean, raw upstream specs without distro-level downstream security hardening overrides."

echo -e "\n=== [AUDIT 3: BUILT-IN ARCHITECTURE TARGETS] ==="
echo "Displaying the host architecture and optimization parameters native to your CPU:"
gcc -v -E - < /dev/null 2>&1 | grep -E 'Target:|Configured with:'

echo -e "\n=== [AUDIT 4: SYSTEM INCLUDE & SEARCH PATHS] ==="
echo "Locating the exact system directories where your compiler pulls its low-level header layers (like sys/mman.h):"
echo | gcc -v -E - 2>&1 | sed -n '/#include <...>/,/End of search list./p'
