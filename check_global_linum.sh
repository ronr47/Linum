#!/bin/bash
echo "===================================================="
echo "LINUM: GLOBAL COMMAND AUDIT"
echo "===================================================="

echo "[*] Checking which 'linum' executables are in your PATH..."
which -a linum || echo "    [!] 'linum' not currently found in active PATH."

echo "[*] Checking local bin links or wrappers..."
if [ -f "./bin/linum" ]; then
    echo "    [OK] Found local binary at ./bin/linum"
    file ./bin/linum
fi

if [ -f "./linum/bin/linum" ]; then
    echo "    [OK] Found local binary at ./linum/bin/linum"
    file ./linum/bin/linum
fi

if [ -f "./venv/bin/linum" ]; then
    echo "    [OK] Found virtual environment binary at ./venv/bin/linum"
    file ./venv/bin/linum
fi

echo "[*] Checking current shell alias or function bindings..."
alias linum || echo "    [!] No shell alias currently set for 'linum'."

echo "===================================================="
echo "AUDIT COMPLETE."
echo "===================================================="
