from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Agriculture Gateway Service")

@app.get("/")
async def root():
    return {"service": "gateway", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
