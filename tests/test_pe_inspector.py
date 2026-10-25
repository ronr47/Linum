import struct
import unittest

from apps.pe_inspector.cli import FormatError, inspect_elf, inspect_pe


def minimal_pe():
    b = bytearray(0x200)
    b[:2] = b"MZ"
    struct.pack_into("<I", b, 0x3C, 0x80)
    b[0x80:0x84] = b"PE\0\0"
    coff = 0x84
    struct.pack_into("<HHIIIHH", b, coff,
                     0x8664, 0, 0, 0, 0, 240, 0x0022)
    opt = coff + 20
    struct.pack_into("<H", b, opt, 0x20B)
    struct.pack_into("<I", b, opt + 16, 0x1000)
    struct.pack_into("<Q", b, opt + 24, 0x140000000)
    struct.pack_into("<II", b, opt + 32, 0x1000, 0x200)
    struct.pack_into("<I", b, opt + 56, 0x2000)
    struct.pack_into("<I", b, opt + 60, 0x200)
    struct.pack_into("<H", b, opt + 68, 10)
    return bytes(b)


def minimal_elf():
    b = bytearray(64)
    b[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<HHIQQQIHHHHHH", b, 16,
                     2, 62, 1, 0x400078, 0, 0, 0,
                     64, 56, 0, 64, 0, 0)
    return bytes(b)


class InspectorTests(unittest.TestCase):
    def test_pe32_plus_header(self):
        result = inspect_pe(minimal_pe())
        self.assertEqual(result["format"], "PE32+")
        self.assertEqual(result["machine_name"], "AMD64")
        self.assertEqual(result["entry_rva"], "0x1000")

    def test_reject_truncated_pe(self):
        with self.assertRaises(FormatError):
            inspect_pe(b"MZ")

    def test_elf64_header(self):
        result = inspect_elf(minimal_elf())
        self.assertEqual(result["format"], "ELF64")
        self.assertEqual(result["machine_name"], "x86-64")
        self.assertEqual(result["entry"], "0x400078")

    def test_reject_wrong_elf_class(self):
        b = bytearray(minimal_elf())
        b[4] = 1
        with self.assertRaises(FormatError):
            inspect_elf(bytes(b))


if __name__ == "__main__":
    unittest.main()
