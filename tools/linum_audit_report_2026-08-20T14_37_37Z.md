# Linum Workspace Audit Report

- **Audit Timestamp:** `2026-08-20T14:37:37Z`
- **Working Directory:** `/home/ron/linum`
- **Git Branch:** `main`
- **Head Commit:** `3491489`

---

## 1. Git Repository State

```text
 M fix_hardcore_theme_and_tests.sh
 M fix_verifier_and_deploy_nala_fx.sh
?? bin_clang
?? bin_gcc
?? bounty_hunter.py
?? bounty_scout.py
?? fix_syntax_errors.sh
?? full_linum_audit.sh
?? graphql_scout.py
?? inspect_broken_heredocs.sh
?? install_all_remaining.sh
?? install_aux_compilers.sh
?? linum_audit_report_2026-08-20T14_31_21Z.md
?? linum_audit_report_2026-08-20T14_32_06Z.md
?? linum_audit_report_2026-08-20T14_37_37Z.md
?? linum_bulletproof_harness
?? linum_bulletproof_harness.rs
?? linum_compiler_core
?? linum_compiler_core.rs
?? linum_compiler_probe
?? linum_compiler_probe.rs
?? linum_omnibus_dispatch
?? linum_omnibus_dispatch.rs
?? linum_polyglot_core
?? linum_polyglot_core.rs
?? linum_stage_1
?? linum_stage_1.rs
?? linum_stage_generator
?? linum_stage_generator.rs
?? linum_z3_prover
?? linum_z3_prover.rs
?? node/
?? patch_broken_scripts.sh
?? pitch_payload.json
?? run_readonly_linum_audit.sh
?? send_pitch.py
?? submit_terminal_pitch.sh
?? target_unit.c
?? test_linum_aux.sh
?? test_linum_omnibus.sh
?? test_llvm21_native.sh
?? test_qbe_pipeline.sh
?? turso/
?? verify_bound.smt2
```

## 2. Source Code vs Artifact Breakdown

| File Category | Extension / Pattern | Count |
| :--- | :--- | :--- |
| Rust Sources | `*.rs` | 59 |
| Python Scripts | `*.py` | 72 |
| Shell Automations | `*.sh` | 180 |
| Linum DSL Files | `*.linum` | 13 |
| Compiled Object Artifacts | `*.o` | 13 |
| Intermediate / IR / Formal Specs | `*.ll`, `*.mlir`, `*.smt2` | 16 |

## 3. Shell Script Audit (Executable Permissions & Validation)

| Script Name | Executable | Syntax Check (bash -n) |
| :--- | :--- | :--- |
| `align_linum_truth.sh` | Yes \vert{}Valid |
| `bench_and_verify_all.sh` | Yes \vert{}Valid |
| `build_and_test.sh` | Yes \vert{}Valid |
| `build_with_linum.sh` | Yes \vert{}Valid |
| `deploy_distributed_mesh_sealed.sh` | Yes \vert{}Valid |
| `deploy_distributed_mesh.sh` | Yes \vert{}Valid |
| `deploy_linum_2050_omniverse.sh` | Yes \vert{}Valid |
| `deploy_production_sealed.sh` | Yes \vert{}Valid |
| `deploy_wasi_and_vector.sh` | Yes \vert{}Valid |
| `fix_all_repos.sh` | Yes \vert{}Valid |
| `fix_and_deploy_native_mesh.sh` | Yes \vert{}Valid |
| `fix_cli_telemetry.sh` | Yes \vert{}Valid |
| `fix_crucible_and_llvm.sh` | Yes \vert{}Valid |
| `fix_crucible_definitive.sh` | Yes \vert{}Valid |
| `fix_driver_namespace.sh` | Yes \vert{}Valid |
| `fix_epistemic_crucible.sh` | Yes \vert{}Valid |
| `fix_github_connectivity.sh` | Yes \vert{}Valid |
| `fix_hardcore_theme_and_tests.sh` | Yes \vert{}Valid |
| `fix_linum_truth_gate_definitive.sh` | Yes \vert{}Valid |
| `fix.sh` | Yes \vert{}Valid |
| `fix_syntax_errors.sh` | Yes \vert{}Valid |
| `fix_verifier_and_deploy_nala_fx.sh` | Yes \vert{}Valid |
| `full_linum_audit.sh` | Yes \vert{}Valid |
| `full_workspace_audit.sh` | Yes \vert{}Valid |
| `implement_ai_future_remedy.sh` | Yes \vert{}Valid |
| `inspect_broken_heredocs.sh` | Yes \vert{}Valid |
| `install_2050_hypervisor.sh` | Yes \vert{}Valid |
| `install_all_remaining.sh` | Yes \vert{}Valid |
| `install_aux_compilers.sh` | Yes \vert{}Valid |
| `install_truth_hook.sh` | Yes \vert{}Valid |
| `linum_build_pipeline.sh` | Yes \vert{}Valid |
| `linum_heredoc_family.sh` | Yes \vert{}Valid |
| `linum_truth_gate.sh` | Yes \vert{}Valid |
| `organize_workspace_truth.sh` | Yes \vert{}Valid |
| `patch_broken_scripts.sh` | Yes \vert{}Valid |
| `patch_driver_native.sh` | Yes \vert{}Valid |
| `repair_and_deploy_mesh.sh` | Yes \vert{}Valid |
| `repair_and_seal_crucible.sh` | Yes \vert{}Valid |
| `restore_hardcore_pipeline.sh` | Yes \vert{}Valid |
| `run_epistemic_crucible.sh` | Yes \vert{}Valid |
| `run_full_pipeline_verification.sh` | Yes \vert{}Valid |
| `run_readonly_linum_audit.sh` | Yes \vert{}Valid |
| `run_truth_gate.sh` | Yes \vert{}Valid |
| `run_workspace_triage_audit.sh` | Yes \vert{}Valid |
| `seal_and_push_github.sh` | Yes \vert{}Valid |
| `setup_2050_hud.sh` | Yes \vert{}Valid |
| `setup_cranelift_jit.sh` | Yes \vert{}Valid |
| `setup_github_auth.sh` | Yes \vert{}Valid |
| `setup_mlir_dialect.sh` | Yes \vert{}Valid |
| `setup_tree_sitter_lsp.sh` | Yes \vert{}Valid |
| `setup_unified_driver.sh` | Yes \vert{}Valid |
| `submit_terminal_pitch.sh` | Yes \vert{}Valid |
| `sync_all_ssh.sh` | Yes \vert{}Valid |
| `test_linum_aux.sh` | Yes \vert{}Valid |
| `test_linum_omnibus.sh` | Yes \vert{}Valid |
| `test_llvm21_native.sh` | Yes \vert{}Valid |
| `test_qbe_pipeline.sh` | Yes \vert{}Valid |
| `upgrade_linum_future_ui.sh` | Yes \vert{}Valid |
| `upgrade_main_terminal.sh` | Yes \vert{}Valid |
| `wire_aya_ebpf_loader.sh` | Yes \vert{}Valid |
| `wire_compiler_runtimes.sh` | Yes \vert{}Valid |
| `wire_mlir_opt.sh` | Yes \vert{}Valid |
| `wire_pyo3_cranelift.sh` | Yes \vert{}Valid |

## 4. Root Rust Artifacts & Source Mapping

| Rust Source | Corresponding Binary Present |
| :--- | :--- |
| `ffi.rs` | No |
| `linum_bulletproof_harness.rs` | Yes (`linum_bulletproof_harness`) |
| `linum_compiler_core.rs` | Yes (`linum_compiler_core`) |
| `linum_compiler_probe.rs` | Yes (`linum_compiler_probe`) |
| `linum_omnibus_dispatch.rs` | Yes (`linum_omnibus_dispatch`) |
| `linum_polyglot_core.rs` | Yes (`linum_polyglot_core`) |
| `linum_stage_1.rs` | Yes (`linum_stage_1`) |
| `linum_stage_generator.rs` | Yes (`linum_stage_generator`) |
| `linum_z3_prover.rs` | Yes (`linum_z3_prover`) |

## 5. Verification & Formal Specification Assets

- **`verify_bound.smt2`**: 15 lines ( bytes)
- **`super_sim.mlir`**: 7 lines ( bytes)
- **`linum_core.ll`**: 20 lines ( bytes)

## 6. Checksum Integrity Summary

Validating against `RELEASE_CHECKSUMS.sha256` (Read-only):
```text
docs/ARCHITECTURE.md: OK
projects/L6_HYPER_SPATIAL.md: OK
projects/mesh_vector.linum: OK
src/linum/ast/biology.py: OK
src/linum/ast/borrow.py: OK
src/linum/ast/__init__.py: OK
src/linum/ast/nodes.py: OK
src/linum/ast/quantum.py: OK
src/linum/ast/regge.py: OK
src/linum/ast/simd.py: OK
src/linum/ast/spacetime.py: OK
src/linum/ast/topological.py: OK
src/linum/bootstrap.c: OK
src/linum/c_auditor.py: OK
src/linum/cli.py: OK
src/linum/compiler.py: OK
src/linum/diagnostics/errors.py: OK
src/linum/diagnostics/__init__.py: OK
src/linum/diagnostics/semantic.py: OK
src/linum/diagnostics/span.py: OK
src/linum/driver.py: OK
src/linum/frontend/__init__.py: OK
src/linum/frontend/lexer.py: OK
src/linum/frontend/parser.py: OK
src/linum/__init__.py: OK
src/linum/lowering/cfg.py: OK
src/linum/lowering/__init__.py: OK
src/linum/lowering/ir.py: OK
src/linum/lowering/llvm.py: OK
src/linum/lowering/ssa.py: OK
src/linum/semantic/analyzer.py: OK
src/linum/semantic/errors.py: OK
src/linum/semantic/__init__.py: OK
src/linum/semantic/types.py: OK
src/linum/semantic/verifier.py: OK
tests/__init__.py: OK
tests/programs/arithmetic.linum: OK
tests/programs/borrow_fail.linum: OK
tests/programs/branch.linum: OK
tests/programs/epistemic_fracture_knot.linum: OK
tests/programs/linear_move_fail.linum: OK
tests/programs/loop.linum: OK
tests/programs/matrix_det_fail.linum: OK
tests/programs/matrix_dim_fail.linum: OK
tests/test_avx512_codegen.py: OK
tests/test_borrow_lifetimes.py: OK
tests/test_c_auditor.py: OK
tests/test_chrono_circuits.py: OK
tests/test_cli.py: OK
tests/test_compiler.py: OK
tests/test_epistemic_crucible.py: OK
tests/test_frontend.py: OK
tests/test_future_ai_remedies.py: OK
tests/test_leak_sentinel.py: OK
tests/test_mesh_chaos.py: OK
tests/test_neuro_symbolic_verifier.py: OK
tests/test_p0_soundness.py: OK
tests/test_phi_type_convergence.py: OK
tests/test_program_pipeline.py: OK
tests/test_regge_calculus.py: OK
tests/test_simd_codegen.py: OK
tests/test_simd_vectorization.py: OK
tests/test_spacetime_metric.py: OK
tests/test_struct_edge_cases.py: OK
tests/test_struct_pipeline.py: OK
tests/test_tensor_dimensions.py: OK
tests/test_topological_braids.py: OK
tests/test_ultimate_truth_invariants.py: OK
tests/test_wetware_synthesis.py: OK
tests/valid_audit_sample.linum: OK
```
