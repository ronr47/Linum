import asyncio
import time

async def fire_ipc_request():
    start_time = time.perf_counter()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", 9090)
        # Use our fast-path memory test command
        writer.write(b"probe-jit\n")
        await writer.drain()
        response = await reader.read(1024)
        writer.close()
        await writer.wait_closed()
        
        # Verify isolation via the returned native payload string
        is_valid = b"Isolation Parameters Secured" in response
        return (time.perf_counter() - start_time) * 1_000_000, is_valid
    except Exception:
        return (time.perf_counter() - start_time) * 1_000_000, False

async def main():
    concurrency_ceiling = 250
    print(f"[Benchmark Matrix] Spawning {concurrency_ceiling} parallel network workers over port 9090...")
    start_total = time.perf_counter()
    tasks = [fire_ipc_request() for _ in range(concurrency_ceiling)]
    results = await asyncio.gather(*tasks)
    end_total = time.perf_counter()

    latencies = [r[0] for r in results]
    successes = sum(1 for r in results if r[1])
    
    print("\n================ BENCHMARK MATRIX STATISTICS ================")
    print(f" Total Concurrent Network Requests : {concurrency_ceiling}")
    print(f" Successfully Verified Isolation  : {successes} / {concurrency_ceiling}")
    print(f" Wall-Clock Execution Horizon      : {(end_total - start_total) * 1000:.2f} ms")
    print(f" Minimum Round-Trip Latency        : {min(latencies):.1f} μs")
    print(f" Average Worker Round-Trip Latency : {sum(latencies)/len(latencies):.1f} μs")
    print("=============================================================")

if __name__ == "__main__":
    asyncio.run(main())
