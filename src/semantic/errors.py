import difflib

class NeuroSymbolicDiagnosticError(TypeError):
    """Raised when symbolic verification fails, offering automated repair suggestions."""
    def __init__(self, message, invalid_field, available_fields):
        suggestions = difflib.get_close_matches(invalid_field, available_fields, n=1, cutoff=0.4)
        if suggestions:
            repair_hint = f"\n💡 Neuro-Symbolic Repair Hint: Did you mean '.{suggestions[0]}'?"
        else:
            repair_hint = f"\n💡 Neuro-Symbolic Repair Hint: Valid structural fields are {list(available_fields)}"
        super().__init__(message + repair_hint)
