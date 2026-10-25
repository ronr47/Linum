# Linum module contract

Every new module must provide:

1. A README documenting purpose, inputs, outputs, dependencies, and failure modes.
2. Explicit input validation and deterministic output.
3. A CLI or library interface independent of the underlying adapter.
4. Structured diagnostics sent to stderr; machine-readable output goes to stdout.
5. Unit tests for valid input, malformed input, truncated input, and boundary cases.
6. No silent fallback, invented success, or mutation of input artifacts.
7. A reproducible invocation and recorded tool/runtime versions.
8. A stated threat model and explicit limitations.

Recommended module layout:

    apps/<module>/
      __init__.py
      cli.py
      domain.py
      ports.py
      adapters.py
    tests/
    README.md

Keep domain logic independent of filesystem, network, and framework code.
Add adapters only when a real external dependency is needed.
