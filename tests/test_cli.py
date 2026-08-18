import pytest
from pathlib import Path
from linum.src.cli import main

def test_cli_emit_llvm_stdout(tmp_path, capsys):
    src_file = tmp_path / "simple.linum"
    src_file.write_text("""
    {
        let x : COPY = %val_42;
        return x;
    }
    """)

    ret = main([str(src_file), "--emit=llvm", "-f", "simple_test"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "define i64 @simple_test" in captured.out
    assert "ret i64" in captured.out

def test_cli_emit_llvm_file(tmp_path):
    src_file = tmp_path / "file.linum"
    out_file = tmp_path / "file.ll"
    src_file.write_text("""
    {
        let q : COPY = %val_42;
        return q;
    }
    """)

    ret = main([str(src_file), "--emit=llvm", "-o", str(out_file), "-f", "file_test"])
    assert ret == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "define i64 @file_test" in content

def test_cli_emit_asm_stdout(tmp_path, capsys):
    src_file = tmp_path / "asm.linum"
    src_file.write_text("""
    {
        let q : COPY = %val_42;
        return q;
    }
    """)

    ret = main([str(src_file), "--emit=asm", "-f", "asm_test"])
    assert ret == 0
    captured = capsys.readouterr()
    assert ("asm_test:" in captured.out or ".globl" in captured.out or "ret" in captured.out)

def test_cli_emit_obj_file(tmp_path):
    src_file = tmp_path / "obj.linum"
    out_obj = tmp_path / "obj.o"
    src_file.write_text("""
    {
        let q : COPY = %val_42;
        return q;
    }
    """)

    ret = main([str(src_file), "--emit=obj", "-o", str(out_obj), "-f", "obj_test"])
    assert ret == 0
    assert out_obj.exists()
    assert out_obj.stat().st_size > 0

def test_cli_rejects_missing_file(capsys):
    ret = main(["non_existent_file.linum"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "input file not found" in captured.err

def test_cli_handles_semantic_verification_failure(tmp_path, capsys):
    src_file = tmp_path / "bad.linum"
    src_file.write_text("""
    {
        let x : COPY = undefined_hallucinated_handle;
        return x;
    }
    """)

    ret = main([str(src_file), "--emit=llvm"])
    assert ret == 1
    captured = capsys.readouterr()
    assert "error [semantic]" in captured.err
