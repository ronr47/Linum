from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LinumDiagnostic:
    kind: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    source: Optional[str] = None

    def render(self) -> str:
        # Resolve global source context code line representation if available
        # fallback layout if file content cache is unpopulated
        location_str = ""
        visual_context = ""
        
        if self.source is not None and self.line is not None:
            location_str = f"{self.source}:{self.line}"
            if self.column is not None:
                location_str += f":{self.column}"
            
            indent = " " * len(str(self.line))
            border = " | "
            
            # Simple fallback line retrieval
            line_text = ""
            if Path(self.source).exists():
                lines = Path(self.source).read_text().splitlines()
                if 0 <= self.line - 1 < len(lines):
                    line_text = lines[self.line - 1]
            
            if line_text:
                caret_pos = max(0, self.column - 1) if self.column else 0
                caret_line = " " * caret_pos + "^"
                visual_context = (
                    f"\n{indent}--> {location_str}"
                    f"\n{indent}|"
                    f"\n{self.line}{border}{line_text}"
                    f"\n{indent}{border}{caret_line}"
                    f"\n{indent}|"
                )
            else:
                visual_context = f"\n{indent}--> {location_str}"

        return (
            f"error[{self.kind}]: {self.message}"
            f"{visual_context}"
        )


class DiagnosticError(Exception):
    def __init__(self, diagnostic: LinumDiagnostic):
        self.diagnostic = diagnostic
        super().__init__(diagnostic.render())

    def __str__(self):
        return self.diagnostic.render()
