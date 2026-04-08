import os
import sys
from fastapi import FastAPI

# Add parent directory to path so it can find mock_network_env
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mock_network_env.env import NetworkIncidentEnv
from mock_network_env.models import NetworkAction

app = FastAPI()
env = NetworkIncidentEnv()

@app.post("/reset")
async def reset_env():
    # The bash script just expects a 200 OK back from this endpoint
    await env.reset()
    return {"status": "ok", "message": "Environment reset successful"}

@app.get("/")
def read_root():
    return {"status": "Network Incident Env is running"}

def main():
    import uvicorn
    # Make sure port 7860 is used for Hugging Face compatibility
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()