#!/usr/bin/env bash
set -e

PY_BIN="$( [ -f "./.venv/bin/python" ] && echo "./.venv/bin/python" || echo "$(which python3)" )"
export PYTHONPATH=".:$PYTHONPATH"

$PY_BIN - <<'PY_EOF'
from pathlib import Path

# 1. Update TokenType and token patterns in src/frontend/lexer.py
lexer_path = Path("src/frontend/lexer.py")
lexer_src = lexer_path.read_text()

# Ensure TokenType enum includes PLUS and MINUS
if "PLUS = " not in lexer_src:
    lexer_src = lexer_src.replace(
        "class TokenType(Enum):",
        "class TokenType(Enum):\n    PLUS = \"+\"\n    MINUS = \"-\""
    )

# Remove the broken IDENTIFIER regex for '+' and '-' and add dedicated token rules
old_bad_rule = "(TokenType.IDENTIFIER, r'[\+\-]'),"
if old_bad_rule in lexer_src:
    lexer_src = lexer_src.replace(
        old_bad_rule,
        "(TokenType.PLUS, r'\\+'),\n            (TokenType.MINUS, r'-'),"
    )
elif "(TokenType.PLUS, r'\\+')" not in lexer_src:
    # Insert after IDENTIFIER pattern if not present
    lexer_src = lexer_src.replace(
        "(TokenType.IDENTIFIER, r'[a-zA-Z_][a-zA-Z_0-9]*'),",
        "(TokenType.IDENTIFIER, r'[a-zA-Z_][a-zA-Z_0-9]*'),\n            (TokenType.PLUS, r'\\+'),\n            (TokenType.MINUS, r'-'),"
    )

lexer_path.write_text(lexer_src)
print("  [+] Fixed src/frontend/lexer.py (added PLUS/MINUS token types).")

# 2. Update src/frontend/parser.py to consume TokenType.PLUS in pointer/binary expressions
parser_path = Path("src/frontend/parser.py")
parser_src = parser_path.read_text()

# Check where pointer offset or addition is parsed
# In parse_expression / parse_statement where "+" was checked as an IDENTIFIER
parser_src = parser_src.replace(
    "tok.type == TokenType.IDENTIFIER and tok.value == \"+\"",
    "tok.type in (TokenType.PLUS, TokenType.IDENTIFIER) and tok.value == \"+\""
)
parser_src = parser_src.replace(
    "tok.type == TokenType.IDENTIFIER and tok.value == \"-\"",
    "tok.type in (TokenType.MINUS, TokenType.IDENTIFIER) and tok.value == \"-\""
)
parser_src = parser_src.replace(
    "self.consume(TokenType.IDENTIFIER)", # if preceded by '+' check
    "self.advance()"
)

parser_path.write_text(parser_src)
print("  [+] Fixed src/frontend/parser.py operator consumption.")
PY_EOF
