from pathlib import Path
from linum.cli import main

def test_leak_sentinel_cli_success(tmp_path, capsys):
    sample = tmp_path / "valid_audit_sample.linum"
    sample.write_text("{\n    let q: COPY = %val_42;\n    return q;\n}")
    
    ret = main([str(sample), "--audit-leak"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "passed all Linum affine/linear leak" in captured.out

def test_leak_sentinel_cli_failure(tmp_path, capsys):
    sample = tmp_path / "invalid_audit_sample.linum"
    sample.write_text("{\n    let q: COPY = %nonexistent_stub;\n    return q;\n}")
    
    ret = main([str(sample), "--audit-leak"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "error" in captured.out.lower()
