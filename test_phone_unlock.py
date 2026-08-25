#!/usr/bin/env python3
import os
import ctypes
import glob

class DeviceContext(ctypes.Structure):
    _fields_ = [
        ("serial_number", ctypes.c_char * 32),
        ("state", ctypes.c_int),
        ("oem_allow_unlocked", ctypes.c_int)
    ]

def run_tests():
    print("=== STARTING PHONE UNLOCKING SUBSYSTEM VERIFICATION ===")
    
    # Locate the compiled shared object in the temp workspace or current dir
    so_files = glob.glob("/tmp/phone_unlock_*/unlock_engine.so")
    if not so_files:
        print("[ERROR] Could not find 'unlock_engine.so'. Run phone_unlock_engine.py first.")
        return
    
    so_path = so_files[0]
    print(f"[*] Loading engine from: {so_path}")
    lib = ctypes.CDLL(so_path)
    eval_func = lib.evaluate_unlock_sequence
    eval_func.argtypes = [ctypes.c_char_p, ctypes.POINTER(DeviceContext)]
    eval_func.restype = ctypes.c_int

    # Test Case 1: Valid Token & OEM Unlocking Enabled
    print("\n--- TEST CASE 1: Valid Token & Authorized OEM State ---")
    target1 = DeviceContext(serial_number=b"TARGET_DEV_01", state=0, oem_allow_unlocked=1)
    status1 = eval_func(b"UNLOCK_SIG_2026_SECURE", ctypes.byref(target1))
    print(f"Status Code: {status1} | State Result: {target1.state} (Expected: 2)")
    assert status1 == 0 and target1.state == 2, "Test 1 Failed!"

    # Test Case 2: Invalid Token Signature
    print("\n--- TEST CASE 2: Invalid Token Signature ---")
    target2 = DeviceContext(serial_number=b"TARGET_DEV_02", state=0, oem_allow_unlocked=1)
    status2 = eval_func(b"MALICIOUS_FAKE_TOKEN", ctypes.byref(target2))
    print(f"Status Code: {status2} | State Result: {target2.state} (Expected: -42)")
    assert status2 == -42 and target2.state == 0, "Test 2 Failed!"

    # Test Case 3: OEM Unlocking Disabled in Settings
    print("\n--- TEST CASE 3: OEM Unlocking Disabled ---")
    target3 = DeviceContext(serial_number=b"TARGET_DEV_03", state=0, oem_allow_unlocked=0)
    status3 = eval_func(b"UNLOCK_SIG_2026_SECURE", ctypes.byref(target3))
    print(f"Status Code: {status3} | State Result: {target3.state} (Expected: -1, Fault: 255)")
    assert status3 == -1 and target3.state == 255, "Test 3 Failed!"

    print("\n[SUCCESS] All security and state transition tests passed successfully!")

if __name__ == "__main__":
    run_tests()
