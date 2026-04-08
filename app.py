from fastapi import FastAPI
from mock_network_env.env import NetworkIncidentEnv

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