"""User API for Flutter - runs on port 8001."""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from user_api.routes import auth, me, stats, trading

app = FastAPI(
    title="VPP User API",
    description="API for Flutter app - user authentication and house management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(stats.router)
app.include_router(trading.router)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "VPP User API", "port": 8001}


@app.get("/health")
def health():
    """Health check."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
