#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "          LINUM: ZERO-ENTROPY WORKSPACE CONVERGENCE         "
echo "============================================================"

# 1. Establish Sovereign Domain Directories
mkdir -p native bpf sophia scripts archive

# 2. Relocate Baremetal, Kernel, and Direct Syscall C/C++ sources
echo "[1/6] Organizing Native / Baremetal Subsystems..."
mv -f beast kernel_entry.* direct_syscall* direct_syscall.c Direct_Syscalls.C \
      Process_Control.C process_control* file_management File_Management.C \
      device_management Device_Management.C communications Communications.C \
      info_management Information_Managemment.C hyper_engine.c engine.c \
      test_arena.c wilc_driver.* x86_64-baremetal-gemic.json \
      compiler_pass_inference.cpp ml_compiler_pass* linker.ld boot.* \
      kernel.elf quantum_circuit.* quantum_runtime.elf Stage* native/ 2>/dev/null || true

# 3. Relocate eBPF & XSK Packet Datapaths
echo "[2/6] Organizing eBPF / XDP Subsystems..."
mv -f bpf_* xdp_prog* xsk_* bpf/ 2>/dev/null || true

# 4. Relocate Sophia Engine Nodes
echo "[3/6] Organizing Sophia Nodes & Snapshots..."
mv -f sophia* vortex* sophia/ 2>/dev/null || true

# 5. Relocate Scripts & Auditing Harnesses
echo "[4/6] Organizing Toolchain Scripts..."
mv -f audit_* fix_* implement_* run_* setup_* snapshot_* update_* verify_* \
      add_* apply_* boot_sync* compile_* deploy_* install_* integrate_* \
      rebuild_* refactor_* system_call* teardown_* toolchain_* scripts/ 2>/dev/null || true

# Preserve primary root entry points
mv -f scripts/linum_truth_gate.sh ./ 2>/dev/null || true
mv -f scripts/full_workspace_audit.sh ./ 2>/dev/null || true

# 6. Archive Raw Debris & Text Chunks
echo "[5/6] Archiving Stale Chunks & Recovery Logs..."
mv -f recovered_* carved_* verification-* linum-compiler.spec \
      docker-compose.yml inspect_* find_* generate_* patch_* read_* archive/ 2>/dev/null || true

# 7. Re-run Verification Gate
echo "[6/6] Executing Truth Gate Verification..."
./linum_truth_gate.sh

echo "============================================================"
echo "         WORKSPACE CONVERGED: ZERO RESIDUAL DEBRIS          "
echo "============================================================"
