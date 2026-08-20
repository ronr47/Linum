#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

cat <<'EOF' > src/linum/lowering/llvm.py
import subprocess
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from linum.semantic.types import FunctionContract, OwnershipMode, Type, PRIMITIVE_INTEGER, PRIMITIVE_BOOLEAN

class LlvmEmitter:
    """
    Translates SSA/CFG intermediate representations into valid LLVM IR.
    Uses unified bidirectional type inference across instructions to ensure
    function signatures and instruction operand types match exactly.
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

    def _clean_name(self, name: Any) -> str:
        if name is None:
            return ""
        if hasattr(name, "name") and hasattr(name, "version"):
            return f"{name.name}.{name.version}".lstrip('%')
        return str(name).lstrip('%')

    def emit(self, cfg: Any, var_types: Dict[str, Any]) -> str:
        self.lines = []
        called_functions: Set[str] = set()
        ret_ty_str = self._type_to_llvm_str(self.contract.return_type)
        blocks = list(cfg.blocks.values()) if isinstance(cfg.blocks, dict) else list(cfg.blocks)

        # 1. Infer types for all variables and SSA registers
        inferred_types: Dict[str, str] = {}

        # Seed from semantic var_types
        for v, t in var_types.items():
            clean_v = self._clean_name(v)
            inferred_types[clean_v] = self._type_to_llvm_str(t)

        # Iterative constraint solving across instructions
        changed = True
        while changed:
            changed = False

            for bb in blocks:
                for phi in getattr(bb, "phis", []):
                    target = self._clean_name(phi.result)
                    target_base = target.split('.')[0]
                    ty = inferred_types.get(target) or inferred_types.get(target_base)
                    
                    if ty:
                        for _, inc_val in phi.incomings:
                            inc_clean = self._clean_name(inc_val)
                            if inc_clean and inferred_types.get(inc_clean) != ty:
                                inferred_types[inc_clean] = ty
                                changed = True

                for instr in bb.instructions:
                    cname = instr.__class__.__name__

                    if cname in ("IrPtrOffset", "PtrOffset"):
                        target = self._clean_name(getattr(instr, "target_reg", None))
                        base = self._clean_name(getattr(instr, "base_ptr", None))
                        offset = self._clean_name(getattr(instr, "offset_reg", None))
                        
                        if target and inferred_types.get(target) != "ptr":
                            inferred_types[target] = "ptr"
                            changed = True
                        if base and inferred_types.get(base) != "ptr":
                            inferred_types[base] = "ptr"
                            changed = True
                        if offset and inferred_types.get(offset) != "i64":
                            inferred_types[offset] = "i64"
                            changed = True

                    elif cname in ("IrPtrLoad", "PtrLoad"):
                        p_var = self._clean_name(getattr(instr, "pointer_var", None))
                        if p_var and inferred_types.get(p_var) != "ptr":
                            inferred_types[p_var] = "ptr"
                            changed = True

                    elif cname in ("IrPtrStore", "PtrStore"):
                        p_var = self._clean_name(getattr(instr, "pointer_var", None))
                        if p_var and inferred_types.get(p_var) != "ptr":
                            inferred_types[p_var] = "ptr"
                            changed = True

                    elif cname in ("IrDrop", "Drop"):
                        p_var = self._clean_name(getattr(instr, "var_name", None))
                        if p_var and inferred_types.get(p_var) != "ptr":
                            inferred_types[p_var] = "ptr"
                            changed = True

                    elif cname in ("IrCall", "Call"):
                        fn = getattr(instr, "function", "")
                        if fn:
                            called_functions.add(fn)
                        if fn in ("free", "__drop_linear_resource"):
                            for arg in getattr(instr, "args_regs", ()):
                                a_clean = self._clean_name(arg)
                                if a_clean and inferred_types.get(a_clean) != "ptr":
                                    inferred_types[a_clean] = "ptr"
                                    changed = True
                        elif fn == "malloc":
                            target = self._clean_name(getattr(instr, "target_reg", None))
                            if target and inferred_types.get(target) != "ptr":
                                inferred_types[target] = "ptr"
                                changed = True
                            for arg in getattr(instr, "args_regs", ()):
                                a_clean = self._clean_name(arg)
                                if a_clean and inferred_types.get(a_clean) != "i64":
                                    inferred_types[a_clean] = "i64"
                                    changed = True

                    elif cname in ("IrAssign", "Assign", "IrStore", "Store"):
                        dest = self._clean_name(getattr(instr, "target_reg", getattr(instr, "dest_var", getattr(instr, "target_var", None))))
                        src = self._clean_name(getattr(instr, "src_reg", None))
                        dest_base = dest.split('.')[0]
                        src_base = src.split('.')[0]

                        dest_ty = inferred_types.get(dest) or inferred_types.get(dest_base)
                        src_ty = inferred_types.get(src) or inferred_types.get(src_base)

                        if dest_ty and not src_ty:
                            inferred_types[src] = dest_ty
                            changed = True
                        elif src_ty and not dest_ty:
                            inferred_types[dest] = src_ty
                            changed = True

                    elif cname in ("IrLoad", "Load"):
                        dest = self._clean_name(getattr(instr, "target_reg", None))
                        src = self._clean_name(getattr(instr, "src_var", None))
                        dest_base = dest.split('.')[0]
                        src_base = src.split('.')[0]

                        dest_ty = inferred_types.get(dest) or inferred_types.get(dest_base)
                        src_ty = inferred_types.get(src) or inferred_types.get(src_base)

                        if dest_ty and not src_ty:
                            inferred_types[src] = dest_ty
                            changed = True
                        elif src_ty and not dest_ty:
                            inferred_types[dest] = src_ty
                            changed = True

                term = getattr(bb, "terminator", None)
                if term:
                    tname = term.__class__.__name__
                    if tname in ("IrCondBranch", "CondBranch"):
                        cond = self._clean_name(getattr(term, "cond_reg", None))
                        if cond and inferred_types.get(cond) != "i1":
                            inferred_types[cond] = "i1"
                            changed = True

        # 2. Collect defined registers vs external environment inputs
        defined_vars: Set[str] = set()
        for bb in blocks:
            for phi in getattr(bb, "phis", []):
                defined_vars.add(self._clean_name(phi.result))
            for instr in bb.instructions:
                t = getattr(instr, "target_reg", None) or getattr(instr, "dest_var", None) or getattr(instr, "target_var", None)
                if t:
                    defined_vars.add(self._clean_name(t))

        discovered_env_params: Dict[str, Tuple[str, str]] = {}

        def collect_operand(op: Optional[Any]):
            if not op:
                return
            clean = self._clean_name(op)
            if clean and clean not in defined_vars and clean not in discovered_env_params:
                clean_base = clean.split('.')[0]
                ty = inferred_types.get(clean) or inferred_types.get(clean_base) or "i64"
                discovered_env_params[clean] = (f"%{clean}_arg", ty)

        for bb in blocks:
            for phi in getattr(bb, "phis", []):
                for _, inc_val in phi.incomings:
                    collect_operand(inc_val)
            for instr in bb.instructions:
                cname = instr.__class__.__name__
                if cname in ("IrAssign", "Assign", "IrStore", "Store"):
                    collect_operand(getattr(instr, "src_reg", None))
                elif cname in ("IrLoad", "Load"):
                    collect_operand(getattr(instr, "src_var", None))
                elif cname in ("IrBinOp", "BinOp"):
                    collect_operand(getattr(instr, "left_reg", None))
                    collect_operand(getattr(instr, "right_reg", None))
                elif cname in ("IrPtrOffset", "PtrOffset"):
                    collect_operand(getattr(instr, "base_ptr", None))
                    collect_operand(getattr(instr, "offset_reg", None))
                elif cname in ("IrPtrLoad", "PtrLoad"):
                    collect_operand(getattr(instr, "pointer_var", None))
                elif cname in ("IrPtrStore", "PtrStore"):
                    collect_operand(getattr(instr, "value_reg", None))
                    collect_operand(getattr(instr, "pointer_var", None))
                elif cname in ("IrDrop", "Drop"):
                    collect_operand(getattr(instr, "var_name", None))
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

        def resolve_op(op: Any) -> str:
            if op is None:
                return ""
            clean = self._clean_name(op)
            if clean in discovered_env_params:
                return discovered_env_params[clean][0]
            return self.format_reg(op)

        def get_type(op: Any) -> str:
            clean = self._clean_name(op)
            clean_base = clean.split('.')[0]
            return inferred_types.get(clean) or inferred_types.get(clean_base) or "i64"

        # 3. Emit external function declarations
        has_drops = any(instr.__class__.__name__ in ("IrDrop", "Drop") for bb in blocks for instr in bb.instructions)
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

        # 4. Emit function signature
        param_strs = []
        for orig_name in sorted(discovered_env_params.keys()):
            arg_name, arg_ty = discovered_env_params[orig_name]
            param_strs.append(f"{arg_ty} {arg_name}")

        params_formatted = ", ".join(param_strs)
        self.lines.append(f"define {ret_ty_str} @{self.contract.name}({params_formatted}) {{")

        # 5. Emit block instructions
        for bb in blocks:
            self.lines.append(f"{bb.label}:")

            for phi in getattr(bb, "phis", []):
                target_fmt = self.format_reg(phi.result)
                ty_str = get_type(phi.result)

                incoming_entries = []
                for block_lbl, inc_val in phi.incomings:
                    inc_fmt = resolve_op(inc_val)
                    block_clean = str(block_lbl).lstrip('%')
                    incoming_entries.append(f"[ {inc_fmt}, %{block_clean} ]")

                phi_str = ", ".join(incoming_entries)
                self.lines.append(f"  {target_fmt} = phi {ty_str} {phi_str}")

            for instr in bb.instructions:
                cname = instr.__class__.__name__

                if cname in ("IrAssign", "Assign"):
                    target_fmt = self.format_reg(instr.target_reg)
                    src_formatted = resolve_op(instr.src_reg)
                    ty_str = get_type(instr.target_reg)

                    if ty_str == "ptr":
                        self.lines.append(f"  {target_fmt} = getelementptr i8, ptr {src_formatted}, i64 0")
                    elif ty_str == "i1":
                        self.lines.append(f"  {target_fmt} = xor i1 {src_formatted}, false")
                    else:
                        self.lines.append(f"  {target_fmt} = add {ty_str} {src_formatted}, 0")

                elif cname in ("IrStore", "Store"):
                    dest = getattr(instr, "dest_var", getattr(instr, "target_var", None))
                    dest_fmt = self.format_reg(dest)
                    src_formatted = resolve_op(instr.src_reg)
                    ty_str = get_type(dest)

                    if ty_str == "ptr":
                        self.lines.append(f"  {dest_fmt} = getelementptr i8, ptr {src_formatted}, i64 0")
                    elif ty_str == "i1":
                        self.lines.append(f"  {dest_fmt} = xor i1 {src_formatted}, false")
                    else:
                        self.lines.append(f"  {dest_fmt} = add {ty_str} {src_formatted}, 0")

                elif cname in ("IrBinOp", "BinOp"):
                    target_fmt = self.format_reg(instr.target_reg)
                    left_fmt = resolve_op(instr.left_reg)
                    right_fmt = resolve_op(instr.right_reg)
                    ty_str = get_type(instr.target_reg)

                    op_inst = "sub" if getattr(instr, "op", "+") == "-" else "add"
                    self.lines.append(f"  {target_fmt} = {op_inst} {ty_str} {left_fmt}, {right_fmt}")

                elif cname in ("IrPtrOffset", "PtrOffset"):
                    target_fmt = self.format_reg(instr.target_reg)
                    base_fmt = resolve_op(instr.base_ptr)
                    offset_fmt = resolve_op(instr.offset_reg)
                    self.lines.append(f"  {target_fmt} = getelementptr i8, ptr {base_fmt}, i64 {offset_fmt}")

                elif cname in ("IrPtrLoad", "PtrLoad"):
                    target_fmt = self.format_reg(instr.target_reg)
                    ptr_fmt = resolve_op(instr.pointer_var)
                    val_ty = get_type(instr.target_reg)
                    self.lines.append(f"  {target_fmt} = load {val_ty}, ptr {ptr_fmt}, align 8")

                elif cname in ("IrPtrStore", "PtrStore"):
                    val_fmt = resolve_op(instr.value_reg)
                    ptr_fmt = resolve_op(instr.pointer_var)
                    val_ty = get_type(instr.value_reg)
                    self.lines.append(f"  store {val_ty} {val_fmt}, ptr {ptr_fmt}, align 8")

                elif cname in ("IrLoad", "Load"):
                    target_fmt = self.format_reg(instr.target_reg)
                    src_formatted = resolve_op(instr.src_var)
                    ty_str = get_type(instr.target_reg)

                    if ty_str == "ptr":
                        self.lines.append(f"  {target_fmt} = getelementptr i8, ptr {src_formatted}, i64 0")
                    elif ty_str == "i1":
                        self.lines.append(f"  {target_fmt} = xor i1 {src_formatted}, false")
                    else:
                        self.lines.append(f"  {target_fmt} = add {ty_str} {src_formatted}, 0")

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
                        formatted_arg = resolve_op(arg)
                        arg_ty = get_type(arg)
                        if fn_name in ("free", "__drop_linear_resource"):
                            arg_ty = "ptr"
                        elif fn_name == "malloc":
                            arg_ty = "i64"
                        arg_strs.append(f"{arg_ty} {formatted_arg}")

                    args_formatted = ", ".join(arg_strs)
                    if instr.target_reg:
                        target_fmt = self.format_reg(instr.target_reg)
                        self.lines.append(f"  {target_fmt} = call {call_ret_ty} @{fn_name}({args_formatted})")
                    else:
                        self.lines.append(f"  call {call_ret_ty} @{fn_name}({args_formatted})")

                elif cname in ("IrDrop", "Drop"):
                    var_fmt = resolve_op(instr.var_name)
                    self.lines.append(f"  call void @__drop_linear_resource(ptr {var_fmt})")

            term = getattr(bb, "terminator", None)
            if term:
                tname = term.__class__.__name__
                if tname in ("IrBranch", "Branch"):
                    self.lines.append(f"  br label %{term.target_label}")
                elif tname in ("IrCondBranch", "CondBranch"):
                    cond_formatted = resolve_op(term.cond_reg)
                    cond_ty = get_type(term.cond_reg)
                    if cond_ty != "i1":
                        cast_reg = f"%cond_cast_{bb.label.lstrip('%')}"
                        self.lines.append(f"  {cast_reg} = icmp ne {cond_ty} {cond_formatted}, 0")
                        cond_formatted = cast_reg
                    self.lines.append(f"  br i1 {cond_formatted}, label %{term.then_label}, label %{term.else_label}")
                elif tname in ("IrReturn", "Return"):
                    if term.val_reg:
                        ret_fmt = resolve_op(term.val_reg)
                        ret_ty = get_type(term.val_reg)
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

echo "src/linum/lowering/llvm.py updated with bidirectional type constraint solving."
