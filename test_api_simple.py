#!/usr/bin/env python3
"""
Simple API test to verify core functionality
"""
import sys
import logging
from fastapi import FastAPI
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_simple_app():
    """Create a minimal FastAPI app for testing"""
    app = FastAPI(title="Trading System API Test", version="1.0.0")
    
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "message": "Simple API test working",
            "system": "Trading System API Test"
        }
    
    @app.get("/")
    async def root():
        return {"message": "Trading System API is running"}
    
    # Test auth endpoint
    @app.post("/auth/test")
    async def test_auth():
        return {"message": "Auth endpoint accessible"}
    
    # Test trades endpoint  
    @app.get("/trades/")
    async def test_trades():
        return {
            "status": "success",
            "trades": [],
            "message": "Trade endpoint accessible"
        }
    
    logger.info("✅ Simple FastAPI app created successfully")
    return app

if __name__ == "__main__":
    try:
        app = create_simple_app()
        logger.info("🚀 Starting simple API test server...")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"❌ Failed to start simple API test: {e}")
        sys.exit(1) 