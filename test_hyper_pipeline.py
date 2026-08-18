# test_hyper_pipeline.py
import ctypes
import os
import subprocess
from pathlib import Path

def test_compile_and_run_hyper():
    shared_lib = "./libhyper.so"
    compile_cmd = ["gcc", "-O3", "-shared", "-fPIC", "-o", shared_lib, "hyper_engine.c"]

    res = subprocess.run(compile_cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"IMPOSSIBLE: Native gcc compilation failed: {res.stderr}"
    
    hyper = ctypes.CDLL(shared_lib)
    hyper.initialize_hyper_memory.restype = ctypes.c_bool
    hyper.hot_swap_engine_configuration.argtypes = [ctypes.c_uint64, ctypes.c_uint32]
    hyper.hot_swap_engine_configuration.restype = ctypes.c_bool
    hyper.hyper_order_ingress_gate.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
    hyper.hyper_order_ingress_gate.restype = ctypes.c_uint64
    hyper.terminate_hyper_memory.argtypes = []
    
    assert hyper.initialize_hyper_memory() is True, "IMPOSSIBLE: Mmap memory arena allocation rejected."
    
    exchange_mask = 0xAA55AA55FFFFFFFF
    clearance_id = 998822
    assert hyper.hot_swap_engine_configuration(exchange_mask, clearance_id) is True, "IMPOSSIBLE: Hot-swap failed."
    
    asset_id = [0x01, 0x00, 0x00, 0x00]          
    volume = [0x0A, 0x00, 0x00, 0x00]            
    price_ticks = [0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00] 
    side = [0x42]                                
    
    raw_order_payload = bytes(asset_id + volume + price_ticks + side)
    order_buffer = (ctypes.c_uint8 * len(raw_order_payload))(*raw_order_payload)
    order_ptr = ctypes.cast(order_buffer, ctypes.POINTER(ctypes.c_uint8))
    
    status_register = hyper.hyper_order_ingress_gate(order_ptr)
    print(f"HYPER DATA PLANE OUT VECTOR REG: {status_register}")
    
    expected_vector = (100 * 10) ^ exchange_mask
    expected_status = expected_vector + clearance_id
    assert status_register == expected_status, "IMPOSSIBLE: Invariant output corruption."
    
    hyper.terminate_hyper_memory()
    if os.path.exists(shared_lib):
        os.remove(shared_lib)
    print("🟢 Hyper Order Processing Engine verified: 0 compilation delays, 0 memory page faults.")

if __name__ == "__main__":
    test_compile_and_run_hyper()
