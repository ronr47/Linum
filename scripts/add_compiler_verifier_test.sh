#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

$PY_BIN - <<'PY_EOF'
from pathlib import Path

test_file = Path("tests/test_compiler.py")
content = test_file.read_text()

if "test_neuro_symbolic_verifier_compiler_rejection" not in content:
    new_test = '''
    def test_neuro_symbolic_verifier_compiler_rejection(self):
        """Validates that untrusted programs with undefined symbols fail at the verifier stage."""
        from linum.compiler import compile_source
        from linum.diagnostics import DiagnosticError

        hallucinated_source = """
        {
            let x : COPY = hallucinated_unbound_symbol;
            return x;
        }
        """
        import pytest
        with pytest.raises(DiagnosticError) as exc_info:
            compile_source(hallucinated_source, "verifier_guard_test")
        
        assert "Hallucinated or undefined identifier" in exc_info.value.diagnostic.message
'''
    # Append inside TestLinumCompiler class
    idx = content.rfind("    def ")
    if idx != -1:
        updated = content + "\n" + new_test
        test_file.write_text(updated)
        print("  [+] Appended test_neuro_symbolic_verifier_compiler_rejection to tests/test_compiler.py")
else:
    print("  [.] Test already exists.")
PY_EOF

echo "Running pytest over all suites..."
$PY_BIN -m pytest -vv
