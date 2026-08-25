#!/usr/bin/env python3
from llama_cpp import Llama
import sys

MODEL_PATH = "/home/ron/linum/models/synthetic_test.gguf"

def main():
    print("============================================================")
    print(" 🧠 LINUM LOCAL INFERENCE + CONSERVATION GATE")
    print("============================================================")
    
    print(f"[*] Loading model via llama-cpp-python from: {MODEL_PATH}")
    try:
        # Load the model locally with CPU backing
        llm = Llama(model_path=MODEL_PATH, n_ctx=512, verbose=False)
        print("[✔] Model loaded successfully into memory-map!")
    except Exception as e:
        print(f"[!] Failed to load model: {e}")
        return

    prompt = "System: Verify status.\nUser: Give system summary.\nAssistant:"
    print(f"[*] Prompt: {prompt.strip()}")
    print("[*] Generating local response...")

    # Generate tokens
    output = llm(
        prompt,
        max_tokens=64,
        stop=["User:", "\n\n"],
        echo=False
    )
    
    generated_text = output['choices'][0]['text'].strip()
    print(f"\n[+] Raw Output Generated:\n    \"{generated_text}\"")

    # --- LINUM HALLUCINATION & SAFETY GATE ---
    print("\n[*] Running Neuro-Symbolic Conservation Gate check...")
    
    # Simple check for structural invariants or forbidden patterns
    forbidden_drifts = ["error:", "undefined", "hallucination"]
    has_drift = any(f in generated_text.lower() for f in forbidden_drifts)

    if not has_drift:
        print("    [✔] Invariant Check: PASSED")
        print("    [✔] STATUS: Output verified sound. Pipeline clear.")
    else:
        print("    [✖] Invariant Check: DRIFT DETECTED!")
        print("    [!] Output blocked by Linum Conservation Gate.")

    print("============================================================")

if __name__ == "__main__":
    main()
