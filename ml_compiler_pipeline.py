import torch
import torch.nn as nn
import torch.onnx
import re

# ==========================================
# 1. SIMPLE FEATURES EXTRACTOR FROM LLVM IR
# ==========================================
class LLVMFeatureExtractor:
    """Parses raw LLVM IR to extract mathematical features for the model."""
    @staticmethod
    def extract_features(llvm_ir_text: str):
        # Quantify the structures that standard heuristics struggle with
        total_instructions = len(llvm_ir_text.strip().split('\n'))
        loop_br_count = len(re.findall(r'br i1', llvm_ir_text))
        phi_nodes = len(re.findall(r'phi ', llvm_ir_text))
        memory_ops = len(re.findall(r'load |store ', llvm_ir_text))
        vector_ops = len(re.findall(r'vector|vscale', llvm_ir_text))

        if total_instructions == 0:
            return [0.0, 0.0, 0.0, 0.0, 0.0]

        # Normalize features relative to basic block size
        return [
            float(total_instructions),
            float(loop_br_count / total_instructions),
            float(phi_nodes / total_instructions),
            float(memory_ops / total_instructions),
            float(vector_ops / total_instructions)
        ]

# ==========================================
# 2. LIGHTWEIGHT COMPILER POLICY NETWORK
# ==========================================
class OptimizationPolicyNet(nn.Module):
    """Predicts a binary decision: Should we unroll/inline this block? (1/0)"""
    def __init__(self, input_dim=5):
        super(OptimizationPolicyNet, self).__init__()
        # Tiny neural network to stay within strict microsecond inference limits
        self.network = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 2) # Outputs Logits: [Don't Optimize, Optimize]
        )

    def forward(self, x):
        return self.network(x)

# ==========================================
# 3. EXPORTING THE MODEL FOR NATIVE AOT 
# ==========================================
if __name__ == "__main__":
    # Sample basic block of LLVM IR code
    sample_llvm_ir = """
    define void @vector_add(float* %a, float* %b, i32 %n) {
    entry:
      %cmp = icmp sgt i32 %n, 0
      br i1 %cmp, label %loop, label %exit
    loop:
      %i = phi i32 [ 0, %entry ], [ %next, %loop ]
      %ptr_a = getelementptr float, float* %a, i32 %i
      %val_a = load float, float* %ptr_a
      %ptr_b = getelementptr float, float* %b, i32 %i
      %val_b = load float, float* %ptr_b
      %add = fadd float %val_a, %val_b
      store float %add, float* %ptr_a
      %next = add nsw i32 %i, 1
      %exitcond = icmp eq i32 %next, %n
      br i1 %exitcond, label %exit, label %loop
    exit:
      ret void
    }
    """
    
    # 1. Convert IR to structural math tensors
    extractor = LLVMFeatureExtractor()
    features = extractor.extract_features(sample_llvm_ir)
    input_tensor = torch.tensor([features], dtype=torch.float32)
    print(f"Extracted IR Features [TotalInst, LoopBr%, Phi%, Mem%, Vec%]:\n{features}\n")

    # 2. Initialize and test the policy network
    model = OptimizationPolicyNet()
    model.eval()
    with torch.no_grad():
        prediction = model(input_tensor)
        decision = torch.argmax(prediction, dim=1).item()
        print(f"Initial Policy Decision: {'OPTIMIZE' if decision == 1 else 'SKIP'}")

    # 3. Export to ONNX file format for deployment to C++ compiler
    onnx_filename = "compiler_policy.onnx"
    torch.onnx.export(
        model, 
        input_tensor, 
        onnx_filename,
        export_params=True,
        opset_version=11,
        input_names=['input_ir_features'],
        output_names=['optimization_decision_logits']
    )
    print(f"Model successfully saved to '{onnx_filename}' for production integration.")
