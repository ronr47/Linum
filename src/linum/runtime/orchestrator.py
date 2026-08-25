"""
LINUM unified execution orchestrator.

This is the layer that turns the collection of existing toolchains into
one coherent compiler/runtime interface.
"""

from dataclasses import dataclass
from typing import Optional

from linum.backends import get_backend, list_backends
from linum.backends.registry import initialize


_INITIALIZED = False


def ensure_initialized() -> None:
    global _INITIALIZED

    if not _INITIALIZED:
        initialize()
        _INITIALIZED = True


@dataclass
class CompilationResult:
    backend: str
    artifact: object


class LinumOrchestrator:

    def __init__(self):
        ensure_initialized()

    def backends(self):
        return list_backends()

    def status(self):
        return {
            backend.name: backend.available()
            for backend in self.backends()
        }

    def emit(
        self,
        backend_name: str,
        llvm_ir: str,
        output: Optional[str] = None,
    ) -> CompilationResult:

        backend = get_backend(backend_name)

        if not backend.available():
            raise RuntimeError(
                f"LINUM backend '{backend_name}' is unavailable"
            )

        if backend_name == "llvm":
            artifact = backend.emit(
                llvm_ir,
                output=output,
            )

        elif backend_name == "asm":
            artifact = backend.emit(
                llvm_ir,
                output=output,
            )

        elif backend_name == "obj":
            if not output:
                raise ValueError(
                    "object backend requires an output path"
                )

            artifact = backend.emit(
                llvm_ir,
                output=output,
            )

        elif backend_name == "bpf":
            if not output:
                raise ValueError(
                    "BPF backend requires an output path"
                )

            artifact = backend.emit(
                llvm_ir,
                output,
            )

        else:
            raise ValueError(
                f"backend '{backend_name}' does not support "
                "LINUM IR emission"
            )

        return CompilationResult(
            backend=backend_name,
            artifact=artifact,
        )
