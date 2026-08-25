"""eBPF backend adapter."""

import shutil
import subprocess


def available() -> bool:
    return shutil.which("clang") is not None


def emit(llvm_ir: str, output: str) -> str:
    if not available():
        raise RuntimeError("clang is required for the eBPF backend")

    command = [
        "clang",
        "-O2",
        "-target",
        "bpf",
        "-x",
        "ir",
        "-c",
        "-",
        "-o",
        output,
    ]

    process = subprocess.run(
        command,
        input=llvm_ir.encode("utf-8"),
        capture_output=True,
    )

    if process.returncode != 0:
        raise RuntimeError(
            "BPF compilation failed:\n"
            + process.stderr.decode("utf-8", errors="replace")
        )

    return output


def register() -> None:
    from . import register_backend

    register_backend(
        "bpf",
        "kernel",
        "Linux eBPF object generation",
        emit,
        available,
    )
