#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

echo "============================================================"
echo "              LINUM UNIFIED BUILD / RUN"
echo "============================================================"

if [[ $# -lt 1 ]]; then
    echo
    echo "Usage:"
    echo "  ./run_linum.sh <file.linum> [llvm|asm|obj|bpf] [output]"
    echo "  ./run_linum.sh <file.linum> run"
    echo
    echo "Examples:"
    echo "  ./run_linum.sh tests/programs/arithmetic.linum llvm arithmetic.ll"
    echo "  ./run_linum.sh tests/programs/arithmetic.linum asm arithmetic.s"
    echo "  ./run_linum.sh tests/programs/arithmetic.linum obj arithmetic.o"
    echo "  ./run_linum.sh tests/programs/arithmetic.linum bpf arithmetic_bpf.o"
    echo "  ./run_linum.sh tests/programs/arithmetic.linum run"
    echo
    exit 2
fi

INPUT="$1"
MODE="${2:-llvm}"
OUTPUT="${3:-}"

if [[ ! -f "$INPUT" ]]; then
    echo "ERROR: input file not found: $INPUT" >&2
    exit 1
fi

echo
echo "[1/6] Python syntax check"

"$PYTHON" -m py_compile \
    src/linum/cli.py \
    src/linum/compiler.py \
    src/linum/driver.py \
    src/linum/backends/__init__.py \
    src/linum/backends/native.py \
    src/linum/backends/bpf.py \
    src/linum/backends/quantum.py \
    src/linum/backends/registry.py \
    src/linum/runtime/__init__.py \
    src/linum/runtime/orchestrator.py

echo "[✔] Python sources compile"

echo
echo "[2/6] Installing Linum editable"

"$PYTHON" -m pip install -e . >/dev/null

echo "[✔] Linum installed"

echo
echo "[3/6] Checking unified backend registry"

"$PYTHON" - <<'PY'
from linum.runtime import LinumOrchestrator

runtime = LinumOrchestrator()

for backend in runtime.backends():
    available = backend.available()
    state = "READY" if available else "UNAVAILABLE"
    print(
        f"[{'✔' if available else '✘'}] "
        f"{backend.name:10} "
        f"{backend.kind:10} "
        f"{state:12} "
        f"{backend.description}"
    )
PY

echo
echo "[4/6] Checking CLI"

"$PYTHON" -m linum.cli --help >/dev/null

echo "[✔] CLI operational"

echo
echo "[5/6] Compiling"

case "$MODE" in
    llvm|asm|obj|bpf)
        ARGS=("$INPUT" "--emit" "$MODE")

        if [[ -n "$OUTPUT" ]]; then
            ARGS+=("--output" "$OUTPUT")
        fi

        echo "[▶] Input : $INPUT"
        echo "[▶] Target: $MODE"

        "$PYTHON" -m linum.cli "${ARGS[@]}"

        if [[ -n "$OUTPUT" && ! -f "$OUTPUT" ]]; then
            echo "ERROR: expected artifact was not created: $OUTPUT" >&2
            exit 1
        fi

        echo
        echo "[✔] Compilation completed"

        if [[ -n "$OUTPUT" ]]; then
            echo "[✔] Artifact: $OUTPUT"
            file "$OUTPUT"
        fi
        ;;

    run)
        echo "[▶] Input : $INPUT"
        echo "[▶] Mode  : native execution"

        TMPDIR="$(mktemp -d)"
        trap 'rm -rf "$TMPDIR"' EXIT

        LLVM="$TMPDIR/linum.ll"
        OBJ="$TMPDIR/linum.o"
        EXE="$TMPDIR/linum_program"

        echo
        echo "[5a/6] Generating LLVM IR"

        "$PYTHON" -m linum.cli \
            "$INPUT" \
            --emit llvm \
            --output "$LLVM"

        [[ -f "$LLVM" ]] || {
            echo "ERROR: LLVM artifact was not created" >&2
            exit 1
        }

        echo "[✔] LLVM IR generated"

        echo
        echo "[5b/6] Compiling LLVM IR to native object"

        if command -v clang >/dev/null 2>&1; then
            clang -c "$LLVM" -o "$OBJ"
        else
            echo "ERROR: clang is required for --run" >&2
            exit 1
        fi

        echo "[✔] Native object generated"

        echo
        echo "[5c/6] Creating execution harness"

        cat > "$TMPDIR/harness.c" <<'C'
#include <stdio.h>

extern long linum_main(long);

int main(int argc, char **argv)
{
    (void)argv;

    long result = linum_main((long)argc);

    printf("%ld\n", result);

    return 0;
}
C

        echo "[✔] Harness generated"

        echo
        echo "[5d/6] Linking executable"

        if ! sed 's/@main(/@linum_main(/g' "$LLVM" > "$TMPDIR/renamed.ll"; then
            echo "ERROR: unable to prepare execution IR" >&2
            exit 1
        fi

        clang -c "$TMPDIR/renamed.ll" -o "$OBJ"
        clang "$TMPDIR/harness.c" "$OBJ" -o "$EXE"

        echo "[✔] Executable linked"

        echo
        echo "[6/6] Executing Linum program"
        echo "------------------------------------------------------------"

        set +e
        "$EXE"
        STATUS=$?
        set -e

        echo "------------------------------------------------------------"
        echo "[✔] Linum program exited with status: $STATUS"

        exit "$STATUS"
        ;;

    *)
        echo "ERROR: unknown mode '$MODE'" >&2
        echo
        echo "Valid modes:"
        echo "  llvm"
        echo "  asm"
        echo "  obj"
        echo "  bpf"
        echo "  run"
        exit 2
        ;;
esac

echo
echo "============================================================"
echo "                 LINUM BUILD COMPLETE"
echo "============================================================"
