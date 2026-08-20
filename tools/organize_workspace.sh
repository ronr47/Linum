#!/usr/bin/env bash
set -euo pipefail

cd /home/ron/linum
mkdir -p tools

echo "[*] Moving triage and diagnostic artifacts to ./tools/..."
mv -f inspect_*.sh \
      find_zig.sh \
      locate_12_compilers.sh \
      patch_bpf_emission.sh \
      run_polyglot_samples.sh \
      seal_truth_state.sh \
      test_complete_omnibus.sh \
      tools/ 2>/dev/null || true

echo "[✔] Root workspace organized."
git status --short
