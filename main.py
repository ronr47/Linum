import os
from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

app = FastAPI()

API_KEY_NAME = "x-api-key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Put your generated key here or read from environment variable
EXPECTED_API_KEY = os.environ.get("MY_API_KEY", "PASTE_YOUR_GENERATED_KEY_HERE")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != EXPECTED_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key

@app.get("/")
def read_root():
    return {"message": "Server is running!"}

@app.get("/protected")
def read_protected(api_key: str = Security(verify_api_key)):
    return {"message": "Access granted! Your API key is working."}
