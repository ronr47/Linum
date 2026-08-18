#!/usr/bin/env bash
set -e

echo "=== 1. The Dynamic Parent (Variable Expansion) ==="
cat <<DYNAMIC_EOF
User       : $USER
Home       : $HOME
Active Dir : $(pwd)
Timestamp  : $(date)
DYNAMIC_EOF

echo ""
echo "=== 2. The Literal Child (Quoted Delimiter / Raw Text) ==="
cat <<'RAW_EOF'
Literal variable: $USER
Literal subshell: $(uname -a)
Literal backticks: `whoami`
RAW_EOF

echo ""
echo "=== 3. The Clean Sibling (Tab Stripping with <<- ) ==="
if true; then
	cat <<-INDENTED
	[Tab-Indented] No leading whitespace in output.
	[Tab-Indented] Clean code structure preserved.
	INDENTED
fi

echo ""
echo "=== 4. The Builder Cousin (Writing Config File via Heredoc) ==="
cat <<'CONF' > /tmp/linum_sample.conf
[compiler]
target = "llvm"
opt_level = 3
debug_symbols = true
CONF
cat /tmp/linum_sample.conf

echo ""
echo "=== 5. The Polyglot Uncle (Feeding Python from Shell Heredoc) ==="
python3 <<'PY_EOF'
family = ["Dynamic", "Literal", "Indented", "File Writer", "Polyglot"]
print("All Heredoc family members gathered:")
for idx, member in enumerate(family, start=1):
    print(f"  {idx}. {member}")
print("Status: 100% harmonious.")
PY_EOF

echo ""
echo "=== All family members executed successfully! ==="
