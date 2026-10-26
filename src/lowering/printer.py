"""R2-IR Text Formatter / Pretty Printer."""

from src.lowering.ir import IRModule, IRFunction, BasicBlock

def format_ir_module(mod: IRModule) -> str:
    lines = [f"; Module: {mod.name}", ""]
    for fn in mod.functions:
        lines.append(format_ir_function(fn))
        lines.append("")
    return "\n".join(lines)

def format_ir_function(fn: IRFunction) -> str:
    params_str = ", ".join(str(p) for p in fn.params)
    lines = [f"define @{fn.name}({params_str}) {{"]
    for bb in fn.blocks:
        lines.append(f"{bb.label}:")
        for inst in bb.instructions:
            lines.append(f"    {inst}")
    lines.append("}")
    return "\n".join(lines)
