#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR=".git/hooks"
HOOK_FILE="$HOOK_DIR/pre-commit"

if [ ! -d ".git" ]; then
    echo "[-] Error: Not at the root of a git repository."
    exit 1
fi

mkdir -p "$HOOK_DIR"

cat << 'HOOK_EOF' > "$HOOK_FILE"
#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo "          LINUM: PRE-COMMIT TRUTH CONSTRAINT AUDIT          "
echo "============================================================"

MAX_LINES=200
VIOLATIONS=0

# 1. Enforce max 200 lines of code per linum module
for file in $(git diff --cached --name-only --diff-filter=ACM | grep '\.linum$' || true); do
    if [ -f "$file" ]; then
        LINE_COUNT=$(wc -l < "$file")
        if [ "$LINE_COUNT" -gt "$MAX_LINES" ]; then
            echo "[-] TRUTH VIOLATION: File '$file' has $LINE_COUNT lines (Max: $MAX_LINES)."
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
    fi
done

# 2. Check for missing Decision Records on staged commits
if ! git diff --cached | grep -q "DECISION-RECORD:"; then
    echo "[!] WARNING: No 'DECISION-RECORD:' tag found in staged changes."
fi

if [ "$VIOLATIONS" -gt 0 ]; then
    echo "[-] Audit Failed: The Constraint Lock rejected $VIOLATIONS file(s)."
    exit 1
fi

echo "[✔] All Truth Constraints satisfied."
exit 0
HOOK_EOF

chmod +x "$HOOK_FILE"
echo "[✔] Linum Pre-Commit Constraint Hook installed."
