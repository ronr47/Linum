from dataclasses import dataclass
from typing import Optional

from linum.diagnostics.span import SourceSpan


@dataclass
class SemanticError(TypeError):
    message: str
    span: Optional[SourceSpan] = None

    def __str__(self):
        return self.message
