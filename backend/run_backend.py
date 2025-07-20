#!/usr/bin/env python3
"""
Startup script for Kotori Bot Backend API

This script handles the initialization and startup of the FastAPI backend
for the Kotori Language Learning Bot system.
"""

import os
import sys
import asyncio
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

def check_environment():
    """Check that required environment variables are set."""
    required_vars = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT", 
        "AZURE_OPENAI_DEPLOYMENT_NAME",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_MODEL_NAME"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️  Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        return False
    
    print("✅ All required environment variables are set")
    return True

def check_anki_connection():
    """Check if Anki is running and AnkiConnect is available."""
    try:
        from anki.anki import _check_anki_connection_internal, create_anki_deck
        result = _check_anki_connection_internal()
        if result.status_code == 200:
            print("✅ Anki connection successful")
            _ = create_anki_deck.invoke({
                "deck_name": "Kotori",
            })
            return True
        else:
            print("⚠️  Anki connection failed - some features may not work")
            return False
    except Exception as e:
        print(f"⚠️  Anki connection error: {e}")
        print("   Make sure Anki is running and AnkiConnect addon is installed")
        return False

def main():
    """Main startup function."""
    load_dotenv()
    print("🤖 Starting Kotori Bot Backend API...")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above.")
        sys.exit(1)
    
    # Check Anki (non-blocking)
    check_anki_connection()
    
    # Get configuration
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", 8000))
    debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    print(f"\n🚀 Starting server on {host}:{port}")
    print(f"📊 Debug mode: {debug_mode}")
    print(f"📚 API documentation: http://localhost:{port}/docs")
    print(f"🔌 WebSocket endpoint: ws://localhost:{port}/ws/chat/{{session_id}}")
    
    if debug_mode:
        print("🐛 Running in development mode with auto-reload")
    
    print("\n" + "=" * 50)
    print("💡 Tips:")
    print("   - Make sure Anki is running for full functionality")
    print("   - The React frontend should connect to this backend")
    print("   - Press Ctrl+C to stop the server")
    print("=" * 50 + "\n")
    
    try:
        # Import and run the FastAPI app
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=debug_mode,
            log_level="info" if not debug_mode else "debug",
            access_log=debug_mode
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()