#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

cat <<'EOF' > src/lowering/llvm.py
import subprocess
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from linum.src.semantic.types import FunctionContract, OwnershipMode, Type, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN

class LlvmEmitter:
    """
    Translates SSA/CFG intermediate representations into valid LLVM IR.
    Consumes semantic type definitions and instruction semantics directly
    without relying on register name heuristics.
    """

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

    def _type_to_llvm_str(self, ty: Any) -> str:
        """Converts a semantic Type or string representation into an LLVM IR type string."""
        if ty is None:
            return "i64"
        if isinstance(ty, Type):
            tname = ty.name
        else:
            tname = str(ty)

        t_clean = tname.strip().lower()
        if t_clean in ("ptr", "raw_ptr", "pointer"):
            return "ptr"
        elif t_clean in ("boolean", "bool", "i1"):
            return "i1"
        elif t_clean in ("void",):
            return "void"
        elif t_clean in ("integer", "int", "i64", "copy"):
            return "i64"
        return "i64"

    def _resolve_type(self, var_or_reg: str, var_types: Dict[str, Any], reg_types: Optional[Dict[str, str]] = None) -> str:
        """
        Determines the LLVM type strictly from the semantic type table or recorded register types.
        No substring matching is performed.
        """
        if not var_or_reg:
            return "i64"
        clean = str(var_or_reg).lstrip('%')

        # 1. Check explicit register type map recorded from instruction emissions
        if reg_types and clean in reg_types:
            return reg_types[clean]

        # 2. Check direct variable in semantic var_types table
        if clean in var_types:
            return self._type_to_llvm_str(var_types[clean])

        # 3. Check base variable name for versioned SSA registers (e.g. 'base_ptr.1' -> 'base_ptr')
        base = clean.split('.')[0]
        if base in var_types:
            return self._type_to_llvm_str(var_types[base])

        # 4. Strip numerical trailing index if formatted as base_1
        base_no_idx = re.sub(r'_\d+$', '', base)
        if base_no_idx in var_types:
            return self._type_to_llvm_str(var_types[base_no_idx])

        return "i64"

    def resolve_operand(self, operand_str: Any, discovered_env_params: Dict[str, Tuple[str, str]]) -> str:
        if operand_str is None:
            return ""
        fmt = self.format_reg(operand_str)
        clean = fmt.lstrip('%')
        if clean in discovered_env_params:
            return discovered_env_params[clean][0]
        return fmt

    def emit(self, cfg: Any, var_types: Dict[str, Any]) -> str:
        self.lines = []
        reg_types: Dict[str, str] = {}
        called_functions: Set[str] = set()

        ret_ty_str = self._type_to_llvm_str(self.contract.return_type)

        blocks = list(cfg.blocks.values()) if isinstance(cfg.blocks, dict) else list(cfg.blocks)

        # Collect internal variables defined within the function
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

        # Pass 1: Discover external environment operands and their required types from instruction usage
        discovered_env_params: Dict[str, Tuple[str, str]] = {}

        def collect_operand(op: Optional[Any], explicit_ty: Optional[str] = None):
            if not op:
                return
            fmt = self.format_reg(op)
            clean = fmt.lstrip('%')
            if clean in defined_vars:
                return
            if clean not in discovered_env_params:
                # Deduce type strictly from explicit instruction role or semantic var_types
                if explicit_ty:
                    param_ty = explicit_ty
                else:
                    param_ty = self._resolve_type(clean, var_types, reg_types)
                discovered_env_params[clean] = (f"%{clean}_arg", param_ty)

        for bb in blocks:
            for phi in getattr(bb, "phis", []):
                for block_lbl, inc_val in phi.incomings:
                    collect_operand(inc_val)
            for instr in bb.instructions:
                cname = instr.__class__.__name__
                if cname in ("IrAssign", "Assign", "IrStore"):
                    dest_name = self.format_reg(getattr(instr, "dest_var", getattr(instr, "target_var", getattr(instr, "target_reg", None)))).lstrip('%')
                    dest_ty = self._resolve_type(dest_name, var_types)
                    collect_operand(getattr(instr, "src_reg", None), explicit_ty=dest_ty if dest_ty != "i64" else None)
                elif cname in ("IrLoad", "Load"):
                    collect_operand(getattr(instr, "src_var", None))
                elif cname in ("IrBinOp", "BinOp"):
                    collect_operand(getattr(instr, "left_reg", None))
                    collect_operand(getattr(instr, "right_reg", None))
                elif cname in ("IrPtrOffset", "PtrOffset"):
                    collect_operand(getattr(instr, "base_ptr", None), explicit_ty="ptr")
                    collect_operand(getattr(instr, "offset_reg", None), explicit_ty="i64")
                elif cname in ("IrPtrLoad", "PtrLoad"):
                    collect_operand(getattr(instr, "pointer_var", None), explicit_ty="ptr")
                elif cname in ("IrPtrStore", "PtrStore"):
                    collect_operand(getattr(instr, "value_reg", None))
                    collect_operand(getattr(instr, "pointer_var", None), explicit_ty="ptr")
                elif cname in ("IrDrop", "Drop"):
                    collect_operand(getattr(instr, "var_name", None), explicit_ty="ptr")
                elif cname in ("IrCall", "Call"):
                    fn = getattr(instr, "function", "")
                    for arg in getattr(instr, "args_regs", ()):
                        if fn in ("free", "__drop_linear_resource"):
                            collect_operand(arg, explicit_ty="ptr")
                        elif fn == "malloc":
                            collect_operand(arg, explicit_ty="i64")
                        else:
                            collect_operand(arg)

            term = getattr(bb, "terminator", None)
            if term:
                tname = term.__class__.__name__
                if tname in ("IrCondBranch", "CondBranch"):
                    collect_operand(getattr(term, "cond_reg", None), explicit_ty="i1")
                elif tname in ("IrReturn", "Return"):
                    collect_operand(getattr(term, "val_reg", None))

        # Emit external forward declarations
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
                ty_str = self._resolve_type(target_clean, var_types, reg_types)
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

                    ty_str = self._resolve_type(target_clean, var_types)
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

                    ty_str = self._resolve_type(dest_clean, var_types)
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

                    ty_str = self._resolve_type(target_clean, var_types, reg_types)
                    reg_types[target_clean] = ty_str

                    op_inst = "sub" if getattr(instr, "op", "+") == "-" else "add"
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

                    val_ty = self._resolve_type(target_clean, var_types, reg_types)
                    reg_types[target_clean] = val_ty
                    self.lines.append(f"  {target_fmt} = load {val_ty}, ptr {ptr_fmt}, align 8")

                elif cname in ("IrPtrStore", "PtrStore"):
                    val_fmt = self.resolve_operand(instr.value_reg, discovered_env_params)
                    val_clean = val_fmt.lstrip('%')
                    ptr_fmt = self.resolve_operand(instr.pointer_var, discovered_env_params)

                    val_ty = reg_types.get(val_clean, self._resolve_type(val_clean, var_types))
                    self.lines.append(f"  store {val_ty} {val_fmt}, ptr {ptr_fmt}, align 8")

                elif cname in ("IrLoad", "Load"):
                    target_fmt = self.format_reg(instr.target_reg)
                    target_clean = target_fmt.lstrip('%')
                    src_var = self.format_reg(instr.src_var)
                    resolved_src = self.resolve_operand(src_var, discovered_env_params)
                    resolved_clean = resolved_src.lstrip('%')

                    ty_str = self._resolve_type(src_var, var_types)
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
                            arg_ty = reg_types.get(arg_clean, self._resolve_type(arg_clean, var_types))
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
                        ret_ty = reg_types.get(ret_clean, self._resolve_type(ret_clean, var_types))
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

    @staticmethod
    def compile_to_assembly(llvm_ir: str) -> str:
        """Compiles LLVM IR string into target machine assembly text."""
        try:
            result = subprocess.run(
                ["llc", "-filetype=asm", "-o", "-", "-"],
                input=llvm_ir.encode('utf-8'),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return result.stdout.decode('utf-8')
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else "Unknown llc compilation error"
            raise RuntimeError(f"LLVM assembly generation failed: {err_msg}")

    @staticmethod
    def compile_to_object(llvm_ir: str, output_path: str) -> bool:
        """Compiles LLVM IR string directly to a machine object (.o) binary file."""
        try:
            subprocess.run(
                ["llc", "-filetype=obj", "-o", output_path, "-"],
                input=llvm_ir.encode('utf-8'),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else "Unknown llc compilation error"
            raise RuntimeError(f"LLVM object file generation failed: {err_msg}")
EOF

echo "src/lowering/llvm.py refactored with explicit type maps."
