"""
Quantum backend bridge.

This intentionally starts as an adapter layer. The quantum engine remains
independent from the LINUM frontend until a stable quantum IR is introduced.
"""

import importlib.util


def aer_available() -> bool:
    return (
        importlib.util.find_spec("qiskit") is not None
        and importlib.util.find_spec("qiskit_aer") is not None
    )


def run_aer(circuit, shots=1000):
    if not aer_available():
        raise RuntimeError(
            "Qiskit and Qiskit Aer are required for the Aer backend"
        )

    from qiskit_aer import AerSimulator

    simulator = AerSimulator()

    result = simulator.run(
        circuit,
        shots=shots,
    ).result()

    return result.get_counts(circuit)


def register() -> None:
    from . import register_backend

    register_backend(
        "aer",
        "quantum",
        "Qiskit Aer quantum simulation",
        run_aer,
        aer_available,
    )
