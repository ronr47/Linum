import re
from pathlib import Path

verifier_path = Path("src/linum/semantic/verifier.py")
content = verifier_path.read_text()

# Ensure EpistemicCrucible aliases directly to the sound verification engine
if "class EpistemicCrucible" not in content:
    alias_block = """

# Direct alias for the epistemic verification gate
if "SemanticVerifier" in globals():
    EpistemicCrucible = SemanticVerifier
elif "ConservationGate" in globals():
    EpistemicCrucible = ConservationGate
"""
    verifier_path.write_text(content + alias_block)
    print("  [✔] Bound EpistemicCrucible symbol to semantic verifier.")
else:
    print("  [•] EpistemicCrucible already defined.")
