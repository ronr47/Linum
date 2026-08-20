import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

app = FastAPI(title="Linum Core API", version="1.0.0")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/v1/benchmark/spsc")
def run_spsc_benchmark():
    try:
        # Execute the compiled Stage D binary directly
        result = subprocess.run(
            ["./linum_stage_d_exec"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd="/home/ron/linum"
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)
            
        return PlainTextResponse(content=result.stdout)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
