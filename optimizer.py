import json
import re
from datetime import datetime

class LocalPromptOptimizer:
    def __init__(self):
        self.fillers = r"\b(please|thank you|could you|i think|maybe|just|lets see|kindly)\b"
        
    def strip_noise(self, text: str) -> str:
        cleaned = re.sub(r'\s+', ' ', text).strip()
        cleaned = re.sub(self.fillers, "", cleaned, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', cleaned).strip()

    def structure_payload(self, raw_text: str, category: str = "compiler_spec") -> str:
        optimized_text = self.strip_noise(raw_text)
        
        payload = {
            "meta": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "os": "Debian 14",
                "category": category
            },
            "payload": {
                "content": optimized_text,
                "token_estimate": len(optimized_text.split())
            }
        }
        return json.dumps(payload, separators=(',', ':'))

if __name__ == "__main__":
    raw_input = """
    Hello Ron, could you please analyze the new photonic-neuromorphic memory crossbar architecture 
    to see if it completely bypasses the traditional Von Neumann bottleneck? Make sure it's fast.
    """
    
    optimizer = LocalPromptOptimizer()
    print(optimizer.structure_payload(raw_input))
    
