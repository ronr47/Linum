"""
LINUM unified backend registry.

Backends are adapters around existing compiler/runtime engines.
The frontend and IR remain independent of individual toolchains.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class Backend:
    name: str
    kind: str
    description: str
    emit: Callable
    available: Callable


_REGISTRY: Dict[str, Backend] = {}


def register_backend(
    name: str,
    kind: str,
    description: str,
    emit: Callable,
    available: Callable,
) -> None:
    _REGISTRY[name] = Backend(
        name=name,
        kind=kind,
        description=description,
        emit=emit,
        available=available,
    )


def get_backend(name: str) -> Backend:
    try:
        return _REGISTRY[name]
    except KeyError:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"unknown LINUM backend '{name}'. "
            f"Available backends: {available}"
        )


def list_backends() -> List[Backend]:
    return list(_REGISTRY.values())


def backend_status() -> Dict[str, bool]:
    return {
        name: backend.available()
        for name, backend in _REGISTRY.items()
    }
