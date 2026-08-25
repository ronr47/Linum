from linum.runtime import LinumOrchestrator


def test_unified_registry():
    runtime = LinumOrchestrator()

    status = runtime.status()

    assert "llvm" in status
    assert "asm" in status
    assert "obj" in status
    assert "bpf" in status
    assert "aer" in status
