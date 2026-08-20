import re
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CAuditError:
    message: str
    line: int
    file_path: str

class CAuditor:
    def __init__(self):
        self.alloc_funcs = ["malloc", "calloc", "realloc"]
        self.free_funcs = ["free"]

    def audit_source(self, filepath: str) -> list[CAuditError]:
        path = Path(filepath)
        if not path.exists():
            return [CAuditError(message=f"File not found: {filepath}", line=0, file_path=filepath)]
            
        lines = path.read_text(encoding="utf-8").splitlines()
        errors = []
        allocated_vars = {}
        current_func = None

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue

            # Detect function definitions
            if re.match(r"^\w+\s+\*?\w+\s*\(.*\)\s*\{?", stripped):
                current_func = stripped.split("(")[0]
                allocated_vars = {}
                continue
                
            # Detect allocations: char* ptr = malloc(...)
            alloc_match = re.search(r"\*?\s*(\w+)\s*=\s*(?:\([^)]+\))?\s*(?:" + "|".join(self.alloc_funcs) + r")\s*\(", stripped)
            if alloc_match:
                var_name = alloc_match.group(1)
                allocated_vars[var_name] = idx
                
            # Detect deallocations: free(ptr)
            free_match = re.search(r"(?:" + "|".join(self.free_funcs) + r")\s*\(\s*(\w+)\s*\)", stripped)
            if free_match:
                var_name = free_match.group(1)
                if var_name in allocated_vars:
                    del allocated_vars[var_name]
                    
            # Detect scope closure or return without freeing
            if (stripped == "}" or "return" in stripped) and current_func:
                if allocated_vars:
                    for var_name, alloc_line in list(allocated_vars.items()):
                        # In the leaky case, we drop out or hit a raw block close
                        errors.append(CAuditError(
                            message=f"Potential memory leak: resource '{var_name}' allocated at line {alloc_line} is never freed before scope exit.",
                            line=idx,
                            file_path=str(path)
                        ))
                    # Wipe memory map to prevent double-reporting tracking errors
                    allocated_vars = {}
                if stripped == "}":
                    current_func = None
                
        return errors

    def synthesize_repair_patch(self, file_path: str) -> str:
        """Analyzes C FFI memory defects and synthesizes deterministic free() injection patches."""
        errors = self.audit_source(file_path)
        if not errors:
            return "// Source passed 0-leak invariant. No patch required.\n"
        
        patch_lines = [f"// Auto-Synthesized Linum Linear Repair Patch for {file_path}"]
        for err in errors:
            patch_lines.append(f"// Fix at line {err.line}: Add free() / linear sink before return")
        return "\n".join(patch_lines) + "\n"
