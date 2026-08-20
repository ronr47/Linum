import pytest
from pathlib import Path
from linum.c_auditor import CAuditor
from linum.cli import main

def test_c_auditor_leaky_file(tmp_path, capsys):
    c_file = tmp_path / "leaky.c"
    c_file.write_text("""
    void process_data() {
        char* buffer = malloc(1024);
        if (!buffer) return;
        // forgot to free(buffer) on this path!
    }
    """)
    
    ret = main(["--audit-c", str(c_file)])
    assert ret == 1
    captured = capsys.readouterr()
    assert "Potential memory leak: resource 'buffer'" in captured.err

def test_c_auditor_clean_file(tmp_path, capsys):
    c_file = tmp_path / "clean.c"
    c_file.write_text("""
    void process_data() {
        char* buffer = malloc(1024);
        free(buffer);
    }
    """)
    
    ret = main(["--audit-c", str(c_file)])
    assert ret == 0
    captured = capsys.readouterr()
    assert "passed C FFI memory audit" in captured.out
