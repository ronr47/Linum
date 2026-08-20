#!/usr/bin/env bash
set -e

if [ -n "$VIRTUAL_ENV" ] && [ -f "$VIRTUAL_ENV/bin/python" ]; then
    PY_BIN="$VIRTUAL_ENV/bin/python"
elif [ -f "./.venv/bin/python" ]; then
    PY_BIN="./.venv/bin/python"
else
    PY_BIN="$(which python3)"
fi

echo "=== 1. Checking IR classes across cfg.py and ssa.py ==="
$PY_BIN - <<'PY_EOF'
import linum.lowering.cfg as cfg
import linum.lowering.ssa as ssa

print("cfg exports:", [k for k in dir(cfg) if not k.startswith('_')])
print("ssa exports:", [k for k in dir(ssa) if not k.startswith('_')])
PY_EOF

echo ""
echo "=== 2. Writing duck-typed, class-name dispatched src/linum/lowering/llvm.py ==="

cat <<'EOF' > src/linum/lowering/llvm.py
import subprocess
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from linum.semantic.types import FunctionContract, OwnershipMode, Type

class LlvmEmitter:
    def __init__(self, contract: FunctionContract):
        self.contract = contract
        self.lines: List[str] = []

    def format_reg(self, reg_name: str) -> str:
        if reg_name is None:
            return ""
        if reg_name.startswith('%'):
            return reg_name
        return f"%{reg_name}"

    def _get_type_str(self, var_name: str, var_types: dict, reg_types: dict = None) -> str:
        if var_name is None:
            return "i64"
        clean = var_name.lstrip('%')
        if reg_types and clean in reg_types:
            return reg_types[clean]
        
        if clean in var_types:
            vt = str(var_types[clean]).lower()
            return "ptr" if "ptr" in vt else "i64"
            
        base = re.sub(r'_\d+$', '', clean)
        if base in var_types:
            vt = str(var_types[base]).lower()
            return "ptr" if "ptr" in vt else "i64"

        # Check for typical pointer keywords in registers/stubs
        if any(keyword in clean.lower() for keyword in ["ptr", "buffer", "mem", "raw", "addr", "res_p"]):
            return "ptr"

        return "i64"

    def resolve_operand(self, operand_str: str, discovered_env_params: dict) -> str:
        if operand_str is None:
            return ""
        clean = operand_str.lstrip('%')
        if clean in discovered_env_params:
            return discovered_env_params[clean][0]
        return self.format_reg(operand_str)

    def emit(self, cfg: Any, var_types: Dict[str, str]) -> str:
        self.lines = []
        reg_types: Dict[str, str] = {}
        
        ret_ty_str = "ptr" if (self.contract.return_type.name == "ptr" or "ptr" in self.contract.return_type.name.lower()) else "i64"
        if self.contract.return_type.name == "VOID":
            ret_ty_str = "void"

        blocks = list(cfg.blocks.values()) if isinstance(cfg.blocks, dict) else list(cfg.blocks)

        # Pass 1: Discover external environment operands and their types
        discovered_env_params: Dict[str, Tuple[str, str]] = {}
        
        def collect_operand(op: Optional[str]):
            if not op:
                return
            clean = op.lstrip('%')
            if ("." in op or "_" in op or clean.startswith("raw_") or clean.startswith("uninit_") or clean.startswith("int_") or clean.startswith("offset_")) and clean not in discovered_env_params:
                param_ty = self._get_type_str(clean, var_types)
                discovered_env_params[clean] = (f"%{clean}_arg", param_ty)

        for bb in blocks:
            for instr in bb.instructions:
                cname = instr.__class__.__name__
                if cname in ("IrAssign", "Assign"):
                    collect_operand(getattr(instr, "src_reg", None))
                elif cname in ("IrLoad", "Load"):
                    collect_operand(getattr(instr, "src_var", None))
                elif cname in ("IrBinOp", "BinOp"):
                    collect_operand(getattr(instr, "left_reg", None))
                    collect_operand(getattr(instr, "right_reg", None))
                elif cname in ("IrPtrOffset", "PtrOffset"):
                    collect_operand(getattr(instr, "base_ptr", None))
                    collect_operand(getattr(instr, "offset_reg", None))
                elif cname in ("IrCall", "Call"):
                    for arg in getattr(instr, "args_regs", ()):
                        collect_operand(arg)
            
            term = getattr(bb, "terminator", None)
            if term:
                tname = term.__class__.__name__
                if tname in ("IrCondBranch", "CondBranch"):
                    collect_operand(getattr(term, "cond_reg", None))
                elif tname in ("IrReturn", "Return"):
                    collect_operand(getattr(term, "val_reg", None))

        # Build parameter string
        param_strs = []
        for orig_name in sorted(discovered_env_params.keys()):
            arg_name, arg_ty = discovered_env_params[orig_name]
            param_strs.append(f"{arg_ty} {arg_name}")
            reg_types[arg_name.lstrip('%')] = arg_ty
            
        params_formatted = ", ".join(param_strs)
        self.lines.append(f"define {ret_ty_str} @{self.contract.name}({params_formatted}) {{")

        # Pass 2: Instruction Emission
        for bb in blocks:
            self.lines.append(f"{bb.label}:")
            for instr in bb.instructions:
                cname = instr.__class__.__name__
                
                if cname in ("IrAssign", "Assign"):
                    target_fmt = self.format_reg(instr.target_reg)
                    target_clean = target_fmt.lstrip('%')
                    src_formatted = self.resolve_operand(instr.src_reg, discovered_env_params)
                    src_clean = src_formatted.lstrip('%')
                    
                    ty_str = reg_types.get(src_clean, self._get_type_str(instr.target_reg, var_types, reg_types))
                    reg_types[target_clean] = ty_str

                    if ty_str == "ptr":
                        self.lines.append(f"  {target_fmt} = getelementptr i8, ptr {src_formatted}, i64 0")
                    else:
                        self.lines.append(f"  {target_fmt} = add {ty_str} {src_formatted}, 0")

                elif cname in ("IrBinOp", "BinOp"):
                    target_fmt = self.format_reg(instr.target_reg)
                    target_clean = target_fmt.lstrip('%')
                    left_fmt = self.resolve_operand(instr.left_reg, discovered_env_params)
                    right_fmt = self.resolve_operand(instr.right_reg, discovered_env_params)
                    
                    ty_str = self._get_type_str(instr.target_reg, var_types, reg_types)
                    reg_types[target_clean] = ty_str
                    
                    op_inst = "sub" if instr.op == "-" else "add"
                    self.lines.append(f"  {target_fmt} = {op_inst} {ty_str} {left_fmt}, {right_fmt}")

                elif cname in ("IrPtrOffset", "PtrOffset"):
                    target_fmt = self.format_reg(instr.target_reg)
                    target_clean = target_fmt.lstrip('%')
                    base_fmt = self.resolve_operand(instr.base_ptr, discovered_env_params)
                    offset_fmt = self.resolve_operand(instr.offset_reg, discovered_env_params)
                    
                    reg_types[target_clean] = "ptr"
                    self.lines.append(f"  {target_fmt} = getelementptr i8, ptr {base_fmt}, i64 {offset_fmt}")

                elif cname in ("IrLoad", "Load"):
                    target_fmt = self.format_reg(instr.target_reg)
                    target_clean = target_fmt.lstrip('%')
                    ty_str = self._get_type_str(instr.src_var, var_types, reg_types)
                    reg_types[target_clean] = ty_str

                    if "." in instr.src_var or "_" in instr.src_var:
                        resolved_src = self.resolve_operand(instr.src_var, discovered_env_params)
                        if ty_str == "ptr":
                            self.lines.append(f"  {target_fmt} = getelementptr i8, ptr {resolved_src}, i64 0")
                        else:
                            self.lines.append(f"  {target_fmt} = add {ty_str} {resolved_src}, 0")
                    else:
                        src_clean = instr.src_var.lstrip('%')
                        self.lines.append(f"  {target_fmt} = load {ty_str}, ptr %{src_clean}, align 8")

                elif cname in ("IrCall", "Call"):
                    res_prefix = f"{self.format_reg(instr.target_reg)} = " if instr.target_reg else ""
                    args_list = getattr(instr, "args_regs", ())
                    arg_strs = []
                    for arg in args_list:
                        formatted_arg = self.resolve_operand(str(arg), discovered_env_params)
                        arg_clean = formatted_arg.lstrip('%')
                        arg_ty = reg_types.get(arg_clean, self._get_type_str(str(arg), var_types))
                        arg_strs.append(f"{arg_ty} {formatted_arg}")
                    
                    args_formatted = ", ".join(arg_strs)
                    if instr.target_reg:
                        reg_types[self.format_reg(instr.target_reg).lstrip('%')] = "ptr"
                        self.lines.append(f"  {res_prefix}call ptr @{instr.function}({args_formatted})")
                    else:
                        self.lines.append(f"  call void @{instr.function}({args_formatted})")

                elif cname in ("IrDrop", "Drop"):
                    self.lines.append(f"  call void @__drop_linear_resource(ptr %{instr.var_name.lstrip('%')})")

            term = getattr(bb, "terminator", None)
            if term:
                tname = term.__class__.__name__
                if tname in ("IrBranch", "Branch"):
                    self.lines.append(f"  br label %{term.target_label}")
                elif tname in ("IrCondBranch", "CondBranch"):
                    cond_formatted = self.resolve_operand(term.cond_reg, discovered_env_params)
                    self.lines.append(f"  br i1 {cond_formatted}, label %{term.then_label}, label %{term.else_label}")
                elif tname in ("IrReturn", "Return"):
                    if term.val_reg:
                        ret_var = term.val_reg.lstrip('%')
                        ret_fmt = self.resolve_operand(term.val_reg, discovered_env_params)
                        ret_ty = reg_types.get(ret_fmt.lstrip('%'), reg_types.get(ret_var, self._get_type_str(ret_var, var_types)))
                        self.lines.append(f"  ret {ret_ty} {ret_fmt}")
                    else:
                        self.lines.append(f"  ret {ret_ty_str}")

        self.lines.append("}")
        return "\n".join(self.lines) + "\n"

class SystemBackendLinker:
    @staticmethod
    def verify_llvm_ir(llvm_ir: str) -> bool:
        """Invokes the local llc system binary via a closed pipeline to validate assembly compliance."""
        try:
            subprocess.run(
                ["llc", "-filetype=obj", "-o", os.devnull, "-"],
                input=llvm_ir.encode('utf-8'),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            if hasattr(e, "stderr") and e.stderr:
                print("\n--- LLVM ASYNC RUNTIME ERROR OUTPUT ---")
                print(e.stderr.decode('utf-8', errors='ignore'))
                print("----------------------------------------\n")
            return False
EOF

echo ""
echo "=== 3. Running pytest on tests/test_program_pipeline.py ==="
$PY_BIN -m pytest -vv tests/test_program_pipeline.py
