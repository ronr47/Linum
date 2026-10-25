# Linum Native Binary Inspection Template

A conservative, read-only starter for inspecting PE32+ and ELF64 executable
headers on Termux, Linux, and other Python 3 environments.

## Requirements

- Python 3.10+
- No third-party Python packages required

## Find the actual EFI file

Run:

    find "$HOME" -type f -iname 'BOOTX64.EFI' -print 2>/dev/null

If the file is on a Windows-mounted volume in WSL, locate it from the WSL
environment instead. Termux `$HOME` and WSL `/home/rr` are different filesystems
unless you explicitly copy or mount the file.

## Inspect

From this repository root:

    python3 -m apps.pe_inspector.cli /absolute/path/to/BOOTX64.EFI
    python3 -m apps.pe_inspector.cli --json /absolute/path/to/BOOTX64.EFI

The inspector reads the file without modifying it. A UEFI x64 executable is
normally a PE32+ image; the subsystem field helps distinguish EFI applications
from Windows applications.

## Tests

    make test
    make selfcheck

## Limits

This is a header/section/segment inspector, not a complete PE/COFF or ELF ABI
validator, disassembler, linker, or firmware emulator. Overlap warnings do not
by themselves establish exploitability or invalidity. No binary is executed.
