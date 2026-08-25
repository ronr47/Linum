#!/usr/bin/env python3
"""
================================================================================
PROJECT AETHER: High-Dimensional Neural-Vector & Matrix Optimization Engine
Architecture: Tensor Mapping, Matrix Multiplication, & Gradient Descent Sandbox
================================================================================
"""

import sys
import time
import random

class TensorEngine:
    def __init__(self, system_id="AETHER-CORE-7"):
        self.system_id = system_id
        self.dimensions = 4  # Simplified embedding dimensions for visualization

    def tokenize_and_embed(self, text):
        print(f"\n[PHASE 1: TOKENIZATION & EMBEDDING]")
        print(f" Input Text: '{text}'")
        print(" Converting tokens into high-dimensional numerical vectors...")
        
        # Generate a pseudo-embedding vector representing semantic space
        vector = [round(random.uniform(-1.0, 1.0), 4) for _ in range(self.dimensions)]
        time.sleep(0.3)
        print(f" Resulting Vector Space (Embedding): {vector}")
        return vector

    def execute_matrix_multiplication(self, vector):
        print(f"\n[PHASE 2: MATRIX MULTIPLICATION (TENSOR GRID)]")
        print(" Multiplying vector by internal weight matrix (W)...")
        
        # Simulated 4x4 weight matrix
        weights = [
            [round(random.uniform(0.1, 0.9), 2) for _ in range(self.dimensions)] 
            for _ in range(self.dimensions)
        ]
        
        for r_idx, row in enumerate(weights):
            print(f"   Weight Row {r_idx+1}: {row}")

        # Simple dot product / matrix transformation simulation
        transformed = [
            round(sum(v * w for v, w in zip(vector, row)), 4) 
            for row in weights
        ]
        
        time.sleep(0.3)
        print(f" Output Tensor State: {transformed}")
        return transformed

    def gradient_descent_optimization(self, tensor_state):
        print(f"\n[PHASE 3: GRADIENT DESCENT & LOSS OPTIMIZATION]")
        print(" Calculating loss function and adjusting weights...")
        
        loss = round(random.uniform(0.15, 0.85), 4)
        epochs = 3
        
        for epoch in range(1, epochs + 1):
            loss = round(loss * 0.4, 4)
            time.sleep(0.2)
            print(f"   [Epoch {epoch}/{epochs}] Optimizing weights... Current Loss Error: {loss}")
            
        print(" -> System converged. Optimal probability distribution locked.")
        print("================================================================================")

def main():
    print("================================================================================")
    print(f"[{TensorEngine().system_id}] NEURAL TENSOR ENGINE ONLINE")
    print("Type a phrase to see it converted into high-dimensional math and optimized.")
    print("Type 'exit' or 'quit' to shut down.")
    print("================================================================================")

    engine = TensorEngine()

    while True:
        try:
            user_input = input("\n[AETHER REPL] Enter phrase > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("\n[SHUTDOWN] Safely unmapping tensor memory. Goodbye, Ron.")
                break
                
            vector = engine.tokenize_and_embed(user_input)
            tensor_state = engine.execute_matrix_multiplication(vector)
            engine.gradient_descent_optimization(tensor_state)
            
        except KeyboardInterrupt:
            print("\n[INTERRUPT] Emergency core shutdown initiated.")
            sys.exit(0)

if __name__ == "__main__":
    main()
