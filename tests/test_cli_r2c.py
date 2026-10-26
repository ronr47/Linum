import subprocess
import sys
import unittest
from pathlib import Path

class TestR2CCLI(unittest.TestCase):
    def setUp(self):
        self.cli_path = Path("src/cli/r2c.py")
        self.pb010_path = Path("proofboot_pb010.r2")
        self.assertTrue(self.cli_path.exists())
        self.assertTrue(self.pb010_path.exists())

    def run_cli(self, *args):
        cmd = [sys.executable, str(self.cli_path)] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_cli_check_pb010(self):
        res = self.run_cli(str(self.pb010_path), "--check")
        self.assertEqual(res.returncode, 0, f"CLI stderr: {res.stderr}")
        self.assertIn("[OK] Semantic verification passed", res.stdout)

    def test_cli_emit_ir_pb010(self):
        res = self.run_cli(str(self.pb010_path), "--emit-ir")
        self.assertEqual(res.returncode, 0, f"CLI stderr: {res.stderr}")
        self.assertIn("; Module: proofboot.pb010", res.stdout)
        self.assertIn("define @crc32", res.stdout)
        self.assertIn("define @arbitrate_active_header", res.stdout)
        self.assertIn("define @commit_transition", res.stdout)

    def test_cli_dump_tokens_pb010(self):
        res = self.run_cli(str(self.pb010_path), "--dump-tokens")
        self.assertEqual(res.returncode, 0)
        self.assertIn("STRUCT", res.stdout)
        self.assertIn("FN", res.stdout)

    def test_cli_dump_ast_pb010(self):
        res = self.run_cli(str(self.pb010_path), "--dump-ast")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Header", res.stdout)
        self.assertIn("StorageDevice", res.stdout)

if __name__ == "__main__":
    unittest.main()
