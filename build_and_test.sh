#!/bin/bash
set -e
echo "[*] Compiling core algorithmic paradigm targets..."
gcc -O2 process_control.c -o process_control
gcc -O2 direct_syscall.c -o direct_syscall
gcc -O2 File_Management.C -o file_management
gcc -O2 Device_Management.C -o device_management
gcc -O2 Information_Managemment.C -o info_management
gcc -O2 Communications.C -o communications

echo -e "\n[*] Running comprehensive cross-layer system suite validation:"
echo "--------------------------------------------------------"
./direct_syscall
./process_control | head -n 3
./file_management
./device_management
./info_management
./communications
echo "--------------------------------------------------------"
echo "[*] Validation suite lifecycle completed successfully."
