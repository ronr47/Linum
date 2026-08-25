"""Initialize the unified LINUM backend registry."""

from .native import register as register_native
from .bpf import register as register_bpf
from .quantum import register as register_quantum


def initialize() -> None:
    register_native()
    register_bpf()
    register_quantum()
