from pathlib import Path
import re

path = Path("src/linum/semantic/verifier.py")
text = path.read_text()

# ---------------------------------------------------------------------------
# 1. Add a helper that normalizes SymbolContext lookup results.
# ---------------------------------------------------------------------------

helper = '''
def _symbol_type(sym):
    """Extract the Type from either a symbol object or legacy tuple entry."""
    if isinstance(sym, tuple):
        if not sym:
            raise TypeError("empty symbol-table entry")
        return sym[0]
    return sym.type


def _symbol_mode(sym):
    """Extract ownership mode from either a symbol object or tuple entry."""
    if isinstance(sym, tuple):
        if len(sym) > 1:
            return sym[1]
        return None
    return getattr(sym, "mode", getattr(sym, "ownership_mode", None))


'''

# Put helpers before the first class definition.
if "def _symbol_type(sym):" not in text:
    match = re.search(r"^class\s+", text, re.MULTILINE)
    if not match:
        raise SystemExit("Could not find class boundary in verifier.py")
    text = text[:match.start()] + helper + text[match.start():]

# ---------------------------------------------------------------------------
# 2. Fix the exact failing lookup.
# ---------------------------------------------------------------------------

old = """            if sym:
                return sym.type"""

new = """            if sym:
                return _symbol_type(sym)"""

if old in text:
    text = text.replace(old, new)
else:
    print("WARNING: exact sym.type lookup was not found")

# ---------------------------------------------------------------------------
# 3. Find and fix other verifier accesses to lookup results.
# ---------------------------------------------------------------------------

# These are intentionally conservative. We only rewrite expressions where
# the variable is clearly the result of a symbol lookup.
lines = text.splitlines(True)
out = []
lookup_vars = set()

for line in lines:
    m = re.search(
        r'(\w+)\s*=\s*self\.(?:root_context|context|ctx)\.lookup\(',
        line,
    )
    if m:
        lookup_vars.add(m.group(1))

    for var in list(lookup_vars):
        line = re.sub(
            rf'\b{re.escape(var)}\.type\b',
            f'_symbol_type({var})',
            line,
        )

    out.append(line)

text = "".join(out)
path.write_text(text)

print("Verifier symbol lookup normalization applied.")
