from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int
    length: int = 1


UNKNOWN_SPAN = SourceSpan(
    line=0,
    column=0,
    length=0,
)
