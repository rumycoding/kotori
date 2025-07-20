import os
import sys
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Add the parent directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

# Load environment variables
load_dotenv()

# Import our modules
from .api.routes import router as api_router
from .websocket.chat_handler import websocket_endpoint

# Check for required environment variables
required_env_vars = [
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT", 
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_MODEL_NAME"
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
    print("Some features may not work properly.")

# Create FastAPI app
app = FastAPI(
    title="Kotori Bot API",
    description="Backend API for Kotori Language Learning Bot",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:52600",  # Common React dev server port
        "http://127.0.0.1:52600"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api", tags=["api"])

# WebSocket endpoint
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for chat communication."""
    print(f"WebSocket connection attempt for session: '{session_id}'")
    print(f"WebSocket client: {websocket.client}")
    
    # Validate session ID
    if not session_id or session_id.strip() == "":
        print("ERROR: Empty session ID provided!")
        await websocket.close(code=1008, reason="Session ID is required")
        return
    
    try:
        await websocket_endpoint(websocket, session_id)
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
        # Try to send error message if possible
        try:
            await websocket.close(code=1000, reason=f"Server error: {str(e)}")
        except:
            pass

# Health check at root
@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "Kotori Bot API",
        "version": "1.0.0", 
        "status": "running",
        "endpoints": {
            "api": "/api",
            "docs": "/docs",
            "health": "/api/health",
            "websocket": "/ws/chat/{session_id}"
        }
    }

# Optional: Serve static files if frontend is built
frontend_build_path = os.path.join(os.path.dirname(__file__), "../../frontend/build")
if os.path.exists(frontend_build_path):
    app.mount("/static", StaticFiles(directory=frontend_build_path), name="static")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    print("Starting Kotori Bot API...")
    
    # Test Anki connection
    try:
        from anki.anki import _check_anki_connection_internal
        result = _check_anki_connection_internal()
        if result.status_code == 200:
            print("✓ Anki connection successful")
        else:
            print("⚠ Anki connection failed - some features may not work")
    except Exception as e:
        print(f"⚠ Anki connection error: {e}")
    
    # Test Azure OpenAI configuration
    try:
        if all(os.getenv(var) for var in required_env_vars):
            print("✓ Azure OpenAI configuration found")
        else:
            print("⚠ Azure OpenAI configuration incomplete")
    except Exception as e:
        print(f"⚠ Azure OpenAI configuration error: {e}")
    
    print("Kotori Bot API started successfully!")
    print(f"API documentation available at: http://localhost:8000/docs")
    print(f"WebSocket endpoint: ws://localhost:8000/ws/chat/{{session_id}}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    print("Shutting down Kotori Bot API...")
    
    # Cleanup sessions
    try:
        from .services.session_manager import session_manager
        await session_manager.cleanup_inactive_sessions(0)  # Cleanup all sessions
        print("✓ Session cleanup completed")
    except Exception as e:
        print(f"⚠ Session cleanup error: {e}")
    
    print("Kotori Bot API shutdown complete")

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("BACKEND_PORT", 8000))
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    print(f"Starting server on {host}:{port}")
    print(f"Debug mode: {debug_mode}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug_mode,
        log_level="info" if not debug_mode else "debug"
    )