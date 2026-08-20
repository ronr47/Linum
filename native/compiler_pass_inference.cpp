#include <iostream>
#include <vector>
#include <numeric>
#include <onnxruntime_cxx_api.h>

int main() {
    // 1. Initialize environment and system capabilities
    Ort::Env env(ORT_LOGGING_LEVEL_WARNING, "CompilerPassEnv");
    Ort::SessionOptions session_options;
    session_options.SetIntraOpNumThreads(1); // Set to 1 thread to avoid core thrashing during builds
    session_options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);

    // 2. Load the exported machine learning model
    const char* model_path = "compiler_policy.onnx";
    std::cout << "[Compiler Log] Loading ML Policy model: " << model_path << "...\n";
    Ort::Session session(env, model_path, session_options);

    // 3. Simulated features extracted from a real LLVM IR basic block 
    // Format matches our Python output: [TotalInst, LoopBr%, Phi%, Mem%, Vec%]
    std::vector<float> input_tensor_values = {14.0f, 0.071f, 0.071f, 0.142f, 0.0f};
    std::vector<int64_t> input_shape = {1, 5}; // 1 batch, 5 unique code metrics

    // 4. Wrap structural data into native ONNX tensors
    auto memory_info = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
    Ort::Value input_tensor = Ort::Value::CreateTensor<float>(
        memory_info, 
        input_tensor_values.data(), 
        input_tensor_values.size(), 
        input_shape.data(), 
        input_shape.size()
    );

    // Track input/output node names
    const char* input_names[] = {"input_ir_features"};
    const char* output_names[] = {"optimization_decision_logits"};

    // 5. Execute optimization prediction inline (Takes <1 millisecond)
    auto output_tensors = session.Run(
        Ort::RunOptions{nullptr}, 
        input_names, 
        &input_tensor, 
        1, 
        output_names, 
        1
    );

    // 6. Read structural results
    float* float_raw_logits = output_tensors.front().GetTensorMutableData<float>();
    
    // Choose index with highest logit value (Softmax classification simulation)
    int final_optimization_action = (float_raw_logits[1] > float_raw_logits[0]) ? 1 : 0;

    std::cout << "\n--- Compiler Strategy Executed ---" << std::endl;
    std::cout << "Logit [0] (Skip Optimization): " << float_raw_logits[0] << std::endl;
    std::cout << "Logit [1] (Apply Optimization): " << float_raw_logits[1] << std::endl;
    std::cout << "Decision: " << (final_optimization_action == 1 ? "TRIGGER LOOP UNROLL PASS" : "LEAVE AS-IS") << std::endl;

    return 0;
}
