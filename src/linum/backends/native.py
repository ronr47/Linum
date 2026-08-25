"""Native LINUM backend adapters."""

import shutil

from linum.lowering.llvm import SystemBackendLinker


def llvm_available() -> bool:
    return True


def asm_available() -> bool:
    return True


def obj_available() -> bool:
    return True


def emit_llvm(llvm_ir: str, output=None) -> str:
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(llvm_ir)
    return llvm_ir


def emit_asm(llvm_ir: str, output=None) -> str:
    asm = SystemBackendLinker.compile_to_assembly(llvm_ir)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(asm)

    return asm


def emit_obj(llvm_ir: str, output: str) -> str:
    SystemBackendLinker.compile_to_object(
        llvm_ir,
        output_path=output,
    )
    return output


def register() -> None:
    from . import register_backend

    register_backend(
        "llvm",
        "native",
        "LLVM intermediate representation",
        emit_llvm,
        llvm_available,
    )

    register_backend(
        "asm",
        "native",
        "Native assembly generation",
        emit_asm,
        asm_available,
    )

    register_backend(
        "obj",
        "native",
        "Native object generation",
        emit_obj,
        obj_available,
    )
