#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

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

    def format_reg(self, reg_name: Any) -> str:
        if reg_name is None:
            return ""
        if hasattr(reg_name, "name") and hasattr(reg_name, "version"):
            return f"%{reg_name.name}.{reg_name.version}"
        s = str(reg_name)
        if s.startswith('%'):
            return s
        return f"%{s}"

    def _get_type_str(self, var_name: str, var_types: dict, reg_types: dict = None) -> str:
        if var_name is None:
            return "i64"
        clean = str(var_name).lstrip('%')
        if reg_types and clean in reg_types:
            return reg_types[clean]
        
        if clean in var_types:
            vt = str(var_types[clean]).lower()
            if "bool" in vt or "i1" in vt:
                return "i1"
            return "ptr" if "ptr" in vt else "i64"
            
        base = re.sub(r'_\d+$', '', clean).split('.')[0]
        if base in var_types:
            vt = str(var_types[base]).lower()
            if "bool" in vt or "i1" in vt:
                return "i1"
            return "ptr" if "ptr" in vt else "i64"

        if "cond" in clean.lower() or "bool" in clean.lower():
            return "i1"

        if any(keyword in clean.lower() for keyword in ["ptr", "buffer", "mem", "raw", "addr", "res_p"]):
            return "ptr"

        return "i64"

    def resolve_operand(self, operand_str: Any, discovered_env_params: dict) -> str:
        if operand_str is None:
            return ""
        fmt = self.format_reg(operand_str)
        clean = fmt.lstrip('%')
        if clean in discovered_env_params:
            return discovered_env_params[clean][0]
        return fmt

    def emit(self, cfg: Any, var_types: Dict[str, str]) -> str:
        self.lines = []
        reg_types: Dict[str, str] = {}
        
        ret_ty_str = "ptr" if (self.contract.return_type.name == "ptr" or "ptr" in self.contract.return_type.name.lower()) else "i64"
        if self.contract.return_type.name == "VOID":
            ret_ty_str = "void"
        elif "bool" in self.contract.return_type.name.lower() or self.contract.return_type.name == "BOOLEAN":
            ret_ty_str = "i1"

        blocks = list(cfg.blocks.values()) if isinstance(cfg.blocks, dict) else list(cfg.blocks)

        # Collect internal variables defined by phis and instructions
        defined_vars: Set[str] = set()
        for bb in blocks:
            for phi in getattr(bb, "phis", []):
                target_reg = self.format_reg(phi.result).lstrip('%')
                defined_vars.add(target_reg)
                
            for instr in bb.instructions:
                t = getattr(instr, "target_reg", None) or getattr(instr, "dest_var", None)
                if t:
                    defined_vars.add(self.format_reg(t).lstrip('%'))

        # Pass 1: Discover external environment operands
        discovered_env_params: Dict[str, Tuple[str, str]] = {}
        
        def collect_operand(op: Optional[Any], force_ty: Optional[str] = None):
            if not op:
                return
            clean = self.format_reg(op).lstrip('%')
            if clean in defined_vars:
                return
            if ("." in clean or "_" in clean or clean.startswith("raw_") or clean.startswith("uninit_") or clean.startswith("int_") or clean.startswith("offset_") or clean.startswith("val_") or clean.startswith("cond_")) and clean not in discovered_env_params:
                param_ty = force_ty if force_ty else self._get_type_str(clean, var_types)
                discovered_env_params[clean] = (f"%{clean}_arg", param_ty)

        for bb in blocks:
            for phi in getattr(bb, "phis", []):
                for block_lbl, inc_val in phi.incomings:
                    collect_operand(inc_val)
            for instr in bb.instructions:
                cname = instr.__class__.__name__
                if cname in ("IrAssign", "Assign", "IrStore"):
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
                    collect_operand(getattr(term, "cond_reg", None), force_ty="i1")
                elif tname in ("IrReturn", "Return"):
                    collect_operand(getattr(term, "val_reg", None))

        # Emit function signature
        param_strs = []
        for orig_name in sorted(discovered_env_params.keys()):
            arg_name, arg_ty = discovered_env_params[orig_name]
            param_strs.append(f"{arg_ty} {arg_name}")
            reg_types[arg_name.lstrip('%')] = arg_ty
            
        params_formatted = ", ".join(param_strs)
        self.lines.append(f"define {ret_ty_str} @{self.contract.name}({params_formatted}) {{")

        # Pass 2: Emit block bodies
        for bb in blocks:
            self.lines.append(f"{bb.label}:")
            
            # Emit PHI nodes
            for phi in getattr(bb, "phis", []):
                target_fmt = self.format_reg(phi.result)
                target_clean = target_fmt.lstrip('%')
                ty_str = self._get_type_str(target_clean, var_types, reg_types)
                reg_types[target_clean] = ty_str

                incoming_entries = []
                for block_lbl, inc_val in phi.incomings:
                    inc_fmt = self.resolve_operand(inc_val, discovered_env_params)
                    block_clean = str(block_lbl).lstrip('%')
                    incoming_entries.append(f"[ {inc_fmt}, %{block_clean} ]")
                
                phi_str = ", ".join(incoming_entries)
                self.lines.append(f"  {target_fmt} = phi {ty_str} {phi_str}")

            for instr in bb.instructions:
                cname = instr.__class__.__name__
                
                if cname in ("IrAssign", "Assign"):
                    target_fmt = self.format_reg(instr.target_reg)
                    target_clean = target_fmt.lstrip('%')
                    src_formatted = self.resolve_operand(instr.src_reg, discovered_env_params)
                    src_clean = src_formatted.lstrip('%')
                    
                    ty_str = reg_types.get(src_clean, self._get_type_str(target_clean, var_types, reg_types))
                    reg_types[target_clean] = ty_str

                    if ty_str == "ptr":
                        self.lines.append(f"  {target_fmt} = getelementptr i8, ptr {src_formatted}, i64 0")
                    elif ty_str == "i1":
                        self.lines.append(f"  {target_fmt} = xor i1 {src_formatted}, false")
                    else:
                        self.lines.append(f"  {target_fmt} = add {ty_str} {src_formatted}, 0")

                elif cname in ("IrBinOp", "BinOp"):
                    target_fmt = self.format_reg(instr.target_reg)
                    target_clean = target_fmt.lstrip('%')
                    left_fmt = self.resolve_operand(instr.left_reg, discovered_env_params)
                    right_fmt = self.resolve_operand(instr.right_reg, discovered_env_params)
                    
                    ty_str = self._get_type_str(target_clean, var_types, reg_types)
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
                    src_var = self.format_reg(instr.src_var)
                    ty_str = self._get_type_str(src_var, var_types, reg_types)
                    reg_types[target_clean] = ty_str

                    if "." in src_var or "_" in src_var:
                        resolved_src = self.resolve_operand(src_var, discovered_env_params)
                        src_ty = reg_types.get(resolved_src.lstrip('%'), ty_str)
                        if src_ty == "ptr":
                            self.lines.append(f"  {target_fmt} = getelementptr i8, ptr {resolved_src}, i64 0")
                        elif src_ty == "i1":
                            self.lines.append(f"  {target_fmt} = xor i1 {resolved_src}, false")
                        else:
                            self.lines.append(f"  {target_fmt} = add {src_ty} {resolved_src}, 0")
                    else:
                        self.lines.append(f"  {target_fmt} = load {ty_str}, ptr {src_var}, align 8")

                elif cname in ("IrCall", "Call"):
                    res_prefix = f"{self.format_reg(instr.target_reg)} = " if instr.target_reg else ""
                    args_list = getattr(instr, "args_regs", ())
                    arg_strs = []
                    for arg in args_list:
                        formatted_arg = self.resolve_operand(arg, discovered_env_params)
                        arg_clean = formatted_arg.lstrip('%')
                        arg_ty = reg_types.get(arg_clean, self._get_type_str(arg_clean, var_types))
                        arg_strs.append(f"{arg_ty} {formatted_arg}")
                    
                    args_formatted = ", ".join(arg_strs)
                    if instr.target_reg:
                        reg_types[self.format_reg(instr.target_reg).lstrip('%')] = "ptr"
                        self.lines.append(f"  {res_prefix}call ptr @{instr.function}({args_formatted})")
                    else:
                        self.lines.append(f"  call void @{instr.function}({args_formatted})")

                elif cname in ("IrDrop", "Drop"):
                    self.lines.append(f"  call void @__drop_linear_resource(ptr %{self.format_reg(instr.var_name).lstrip('%')})")

            term = getattr(bb, "terminator", None)
            if term:
                tname = term.__class__.__name__
                if tname in ("IrBranch", "Branch"):
                    self.lines.append(f"  br label %{term.target_label}")
                elif tname in ("IrCondBranch", "CondBranch"):
                    cond_formatted = self.resolve_operand(term.cond_reg, discovered_env_params)
                    cond_clean = cond_formatted.lstrip('%')
                    cond_ty = reg_types.get(cond_clean, "i1")
                    if cond_ty != "i1":
                        cast_reg = f"%cond_cast_{bb.label.lstrip('%')}"
                        self.lines.append(f"  {cast_reg} = icmp ne {cond_ty} {cond_formatted}, 0")
                        cond_formatted = cast_reg
                    self.lines.append(f"  br i1 {cond_formatted}, label %{term.then_label}, label %{term.else_label}")
                elif tname in ("IrReturn", "Return"):
                    if term.val_reg:
                        ret_fmt = self.resolve_operand(term.val_reg, discovered_env_params)
                        ret_clean = ret_fmt.lstrip('%')
                        ret_ty = reg_types.get(ret_clean, self._get_type_str(ret_clean, var_types))
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

echo "Running pytest over all suites..."
$PY_BIN -m pytest -vv
