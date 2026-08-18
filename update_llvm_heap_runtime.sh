#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

cat <<'EOF' > src/lowering/llvm.py
import subprocess
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from linum.src.semantic.types import FunctionContract, OwnershipMode, Type

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
        
        # 1. Direct variable lookup
        if clean in var_types:
            vt = str(var_types[clean]).lower()
            if "bool" in vt or "i1" in vt:
                return "i1"
            return "ptr" if "ptr" in vt else "i64"

        # 2. Versioned variable base lookup
        base = clean.split('.')[0]
        base_no_idx = re.sub(r'_\d+$', '', base)
        if base in var_types:
            vt = str(var_types[base]).lower()
            if "bool" in vt or "i1" in vt:
                return "i1"
            return "ptr" if "ptr" in vt else "i64"
        if base_no_idx in var_types:
            vt = str(var_types[base_no_idx]).lower()
            if "bool" in vt or "i1" in vt:
                return "i1"
            return "ptr" if "ptr" in vt else "i64"

        # 3. Explicit register types recorded from preceding instructions
        if reg_types and clean in reg_types:
            return reg_types[clean]

        # 4. Name-based heuristics
        if "cond" in clean.lower() or "bool" in clean.lower():
            return "i1"

        if any(k in clean.lower() for k in ["ptr", "buffer", "mem", "raw", "addr", "res_p", "stub", "alloc", "heap"]):
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
        called_functions: Set[str] = set()
        
        ret_ty_str = "ptr" if (self.contract.return_type.name == "ptr" or "ptr" in self.contract.return_type.name.lower()) else "i64"
        if self.contract.return_type.name == "VOID":
            ret_ty_str = "void"
        elif "bool" in self.contract.return_type.name.lower() or self.contract.return_type.name == "BOOLEAN":
            ret_ty_str = "i1"

        blocks = list(cfg.blocks.values()) if isinstance(cfg.blocks, dict) else list(cfg.blocks)

        # Collect internal variables defined by phis and instructions
        defined_vars: Set[str] = set()
        has_drops = False
        for bb in blocks:
            for phi in getattr(bb, "phis", []):
                target_reg = self.format_reg(phi.result).lstrip('%')
                defined_vars.add(target_reg)
                
            for instr in bb.instructions:
                t = getattr(instr, "target_reg", None) or getattr(instr, "dest_var", None) or getattr(instr, "target_var", None)
                if t:
                    defined_vars.add(self.format_reg(t).lstrip('%'))
                if instr.__class__.__name__ in ("IrDrop", "Drop"):
                    has_drops = True
                elif instr.__class__.__name__ in ("IrCall", "Call"):
                    called_functions.add(getattr(instr, "function", ""))

        # Track which registers feed into pointer variables
        ptr_registers: Set[str] = set()
        for bb in blocks:
            for instr in bb.instructions:
                cname = instr.__class__.__name__
                if cname in ("IrStore", "Store"):
                    dest = self.format_reg(getattr(instr, "dest_var", getattr(instr, "target_var", None))).lstrip('%')
                    if self._get_type_str(dest, var_types) == "ptr":
                        src = self.format_reg(instr.src_reg).lstrip('%')
                        ptr_registers.add(src)
                elif cname in ("IrAssign", "Assign"):
                    target = self.format_reg(instr.target_reg).lstrip('%')
                    if self._get_type_str(target, var_types) == "ptr":
                        src = self.format_reg(instr.src_reg).lstrip('%')
                        ptr_registers.add(src)
                elif cname in ("IrPtrStore", "PtrStore", "IrPtrLoad", "PtrLoad"):
                    p_var = self.format_reg(getattr(instr, "pointer_var", None)).lstrip('%')
                    ptr_registers.add(p_var)
                elif cname in ("IrCall", "Call") and getattr(instr, "function", "") == "malloc":
                    if instr.target_reg:
                        ptr_registers.add(self.format_reg(instr.target_reg).lstrip('%'))

        # Pass 1: Discover external environment operands
        discovered_env_params: Dict[str, Tuple[str, str]] = {}
        
        def collect_operand(op: Optional[Any], force_ty: Optional[str] = None):
            if not op:
                return
            fmt = self.format_reg(op)
            clean = fmt.lstrip('%')
            if clean in defined_vars:
                return
            if ("." in clean or "_" in clean or clean.startswith("raw_") or clean.startswith("uninit_") or clean.startswith("int_") or clean.startswith("offset_") or clean.startswith("val_") or clean.startswith("cond_") or clean.startswith("size_")) and clean not in discovered_env_params:
                param_ty = force_ty if force_ty else self._get_type_str(clean, var_types)
                if clean in ptr_registers:
                    param_ty = "ptr"
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
                    collect_operand(getattr(instr, "base_ptr", None), force_ty="ptr")
                    collect_operand(getattr(instr, "offset_reg", None), force_ty="i64")
                elif cname in ("IrPtrLoad", "PtrLoad"):
                    collect_operand(getattr(instr, "pointer_var", None), force_ty="ptr")
                elif cname in ("IrPtrStore", "PtrStore"):
                    collect_operand(getattr(instr, "value_reg", None))
                    collect_operand(getattr(instr, "pointer_var", None), force_ty="ptr")
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

        # Emit standard runtime declarations
        declarations = []
        if "malloc" in called_functions:
            declarations.append("declare noalias ptr @malloc(i64)")
        if "free" in called_functions:
            declarations.append("declare void @free(ptr)")
        if has_drops or "__drop_linear_resource" in called_functions:
            declarations.append("declare void @__drop_linear_resource(ptr)")
        
        for decl in declarations:
            self.lines.append(decl)
        if declarations:
            self.lines.append("")

        # Emit function signature
        param_strs = []
        for orig_name in sorted(discovered_env_params.keys()):
            arg_name, arg_ty = discovered_env_params[orig_name]
            param_strs.append(f"{arg_ty} {arg_name}")
            reg_types[arg_name.lstrip('%')] = arg_ty
            reg_types[orig_name] = arg_ty
            
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
                    
                    ty_str = self._get_type_str(target_clean, var_types)
                    if ty_str == "i64" and src_clean in reg_types:
                        ty_str = reg_types[src_clean]
                    reg_types[target_clean] = ty_str

                    if ty_str == "ptr":
                        self.lines.append(f"  {target_fmt} = getelementptr i8, ptr {src_formatted}, i64 0")
                    elif ty_str == "i1":
                        self.lines.append(f"  {target_fmt} = xor i1 {src_formatted}, false")
                    else:
                        self.lines.append(f"  {target_fmt} = add {ty_str} {src_formatted}, 0")

                elif cname in ("IrStore", "Store"):
                    dest_fmt = self.format_reg(getattr(instr, "dest_var", getattr(instr, "target_var", None)))
                    dest_clean = dest_fmt.lstrip('%')
                    src_formatted = self.resolve_operand(instr.src_reg, discovered_env_params)
                    src_clean = src_formatted.lstrip('%')
                    
                    ty_str = self._get_type_str(dest_clean, var_types)
                    if ty_str == "i64" and src_clean in reg_types:
                        ty_str = reg_types[src_clean]
                    reg_types[dest_clean] = ty_str

                    if ty_str == "ptr":
                        self.lines.append(f"  {dest_fmt} = getelementptr i8, ptr {src_formatted}, i64 0")
                    elif ty_str == "i1":
                        self.lines.append(f"  {dest_fmt} = xor i1 {src_formatted}, false")
                    else:
                        self.lines.append(f"  {dest_fmt} = add {ty_str} {src_formatted}, 0")

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

                elif cname in ("IrPtrLoad", "PtrLoad"):
                    target_fmt = self.format_reg(instr.target_reg)
                    target_clean = target_fmt.lstrip('%')
                    ptr_fmt = self.resolve_operand(instr.pointer_var, discovered_env_params)
                    
                    val_ty = self._get_type_str(target_clean, var_types, reg_types)
                    reg_types[target_clean] = val_ty
                    self.lines.append(f"  {target_fmt} = load {val_ty}, ptr {ptr_fmt}, align 8")

                elif cname in ("IrPtrStore", "PtrStore"):
                    val_fmt = self.resolve_operand(instr.value_reg, discovered_env_params)
                    val_clean = val_fmt.lstrip('%')
                    ptr_fmt = self.resolve_operand(instr.pointer_var, discovered_env_params)
                    
                    val_ty = reg_types.get(val_clean, self._get_type_str(val_clean, var_types))
                    self.lines.append(f"  store {val_ty} {val_fmt}, ptr {ptr_fmt}, align 8")

                elif cname in ("IrLoad", "Load"):
                    target_fmt = self.format_reg(instr.target_reg)
                    target_clean = target_fmt.lstrip('%')
                    src_var = self.format_reg(instr.src_var)
                    resolved_src = self.resolve_operand(src_var, discovered_env_params)
                    resolved_clean = resolved_src.lstrip('%')
                    
                    ty_str = self._get_type_str(src_var, var_types)
                    if ty_str == "i64" and resolved_clean in reg_types:
                        ty_str = reg_types[resolved_clean]
                    reg_types[target_clean] = ty_str

                    if ty_str == "ptr":
                        self.lines.append(f"  {target_fmt} = getelementptr i8, ptr {resolved_src}, i64 0")
                    elif ty_str == "i1":
                        self.lines.append(f"  {target_fmt} = xor i1 {resolved_src}, false")
                    else:
                        self.lines.append(f"  {target_fmt} = add {ty_str} {resolved_src}, 0")

                elif cname in ("IrCall", "Call"):
                    fn_name = instr.function
                    args_list = getattr(instr, "args_regs", ())
                    arg_strs = []
                    
                    # Determine call return type
                    if fn_name == "malloc":
                        call_ret_ty = "ptr"
                    elif fn_name in ("free", "__drop_linear_resource"):
                        call_ret_ty = "void"
                    else:
                        call_ret_ty = "ptr" if instr.target_reg else "void"

                    for arg in args_list:
                        formatted_arg = self.resolve_operand(arg, discovered_env_params)
                        arg_clean = formatted_arg.lstrip('%')
                        if fn_name in ("free", "__drop_linear_resource"):
                            arg_ty = "ptr"
                        elif fn_name == "malloc":
                            arg_ty = "i64"
                        else:
                            arg_ty = reg_types.get(arg_clean, self._get_type_str(arg_clean, var_types))
                        arg_strs.append(f"{arg_ty} {formatted_arg}")
                    
                    args_formatted = ", ".join(arg_strs)
                    if instr.target_reg:
                        target_fmt = self.format_reg(instr.target_reg)
                        reg_types[target_fmt.lstrip('%')] = call_ret_ty
                        self.lines.append(f"  {target_fmt} = call {call_ret_ty} @{fn_name}({args_formatted})")
                    else:
                        self.lines.append(f"  call {call_ret_ty} @{fn_name}({args_formatted})")

                elif cname in ("IrDrop", "Drop"):
                    var_fmt = self.resolve_operand(instr.var_name, discovered_env_params)
                    self.lines.append(f"  call void @__drop_linear_resource(ptr {var_fmt})")

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

echo "src/lowering/llvm.py updated successfully."
