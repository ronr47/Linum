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
        location = ""

        if self.source is not None and self.line is not None:
            location = f"{self.source}:{self.line}"
            if self.column is not None:
                location += f":{self.column}"

            location += "\n"

        return (
            f"{location}"
            f"error[{self.kind}]: {self.message}"
        )


class DiagnosticError(Exception):
    def __init__(self, diagnostic: LinumDiagnostic):
        self.diagnostic = diagnostic
        super().__init__(diagnostic.render())

    def __str__(self):
        return self.diagnostic.render()
