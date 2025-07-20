from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from ..models import (
    KotoriConfig, SessionConfig, UISettings, VoiceSettings,
    ConversationHistory, ExportRequest, HealthResponse, ErrorResponse
)
from ..services.session_manager import session_manager, conversation_manager

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    # Check Anki connection
    anki_status = "unknown"
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
        from anki.anki import _check_anki_connection_internal
        
        result = _check_anki_connection_internal()
        if result.status_code == 200:
            anki_status = "connected"
        else:
            anki_status = "disconnected"
    except Exception:
        anki_status = "error"
    
    # Check Azure OpenAI
    azure_status = "unknown"
    try:
        import os
        required_vars = [
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT", 
            "AZURE_OPENAI_DEPLOYMENT_NAME",
            "AZURE_OPENAI_API_VERSION"
        ]
        if all(os.getenv(var) for var in required_vars):
            azure_status = "configured"
        else:
            azure_status = "missing_config"
    except Exception:
        azure_status = "error"
    
    return HealthResponse(
        status="healthy",
        services={
            "anki": anki_status,
            "azure_openai": azure_status,
            "session_manager": "active",
            "conversation_manager": "active"
        }
    )


@router.post("/sessions", response_model=dict)
async def create_session(config: Optional[KotoriConfig] = None):
    """Create a new chat session."""
    try:
        print(f"Creating new session with config: {config}")
        session_id = await session_manager.create_session(config)
        
        # Verify session was created successfully
        created_session = await session_manager.get_session(session_id)
        if created_session is None:
            raise HTTPException(status_code=500, detail="Session creation failed - session not found after creation")
        
        print(f"✓ Session creation confirmed: {session_id}")
        return {
            "session_id": session_id,
            "message": "Session created successfully",
            "timestamp": datetime.now().isoformat(),
            "config": created_session.config.model_dump() if created_session.config else None
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Session creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/sessions/{session_id}", response_model=dict)
async def get_session(session_id: str):
    """Get session information."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session": session.model_dump(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/sessions", response_model=dict)
async def list_sessions():
    """List all active sessions."""
    active_sessions = await session_manager.get_active_sessions()
    total_sessions = await session_manager.get_session_count()
    active_count = await session_manager.get_active_session_count()
    
    return {
        "active_sessions": active_sessions,
        "active_count": active_count,
        "total_sessions": total_sessions,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/sessions/stats", response_model=dict)
async def get_session_stats():
    """Get session statistics."""
    total_sessions = await session_manager.get_session_count()
    active_count = await session_manager.get_active_session_count()
    
    return {
        "total_sessions": total_sessions,
        "active_sessions": active_count,
        "inactive_sessions": total_sessions - active_count,
        "timestamp": datetime.now().isoformat()
    }


@router.put("/sessions/{session_id}/config", response_model=dict)
async def update_session_config(session_id: str, config: KotoriConfig):
    """Update session configuration."""
    success = await session_manager.update_session_config(session_id, config)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "message": "Configuration updated successfully",
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }


@router.put("/sessions/{session_id}/ui-settings", response_model=dict)
async def update_ui_settings(session_id: str, ui_settings: UISettings):
    """Update UI settings for a session."""
    success = await session_manager.update_ui_settings(session_id, ui_settings)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "message": "UI settings updated successfully",
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }


@router.delete("/sessions/{session_id}", response_model=dict)
async def close_session(session_id: str):
    """Close a session permanently."""
    # First deactivate the session
    success = await session_manager.deactivate_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "message": "Session closed successfully",
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/sessions/{session_id}/history", response_model=dict)
async def get_conversation_history(session_id: str, limit: Optional[int] = None):
    """Get conversation history for a session."""
    if limit:
        messages = await conversation_manager.get_recent_messages(session_id, limit)
    else:
        messages = await conversation_manager.get_conversation(session_id)
    
    session = await session_manager.get_session(session_id)
    
    return {
        "session_id": session_id,
        "messages": [msg.model_dump() for msg in messages],
        "message_count": len(messages),
        "session_info": session.model_dump() if session else None,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/sessions/{session_id}/history/export", response_model=dict)
async def export_conversation(session_id: str, export_request: ExportRequest):
    """Export conversation history in specified format."""
    if export_request.session_id != session_id:
        raise HTTPException(status_code=400, detail="Session ID mismatch")
    
    exported_data = await conversation_manager.export_conversation(
        session_id, 
        export_request.format
    )
    
    if exported_data is None:
        raise HTTPException(status_code=400, detail="Invalid export format or no data")
    
    return {
        "session_id": session_id,
        "format": export_request.format,
        "data": exported_data,
        "exported_at": datetime.now().isoformat()
    }


@router.delete("/sessions/{session_id}/history", response_model=dict)
async def clear_conversation_history(session_id: str):
    """Clear conversation history for a session."""
    success = await conversation_manager.clear_conversation(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or no history")
    
    return {
        "message": "Conversation history cleared successfully",
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/anki/status", response_model=dict)
async def check_anki_status():
    """Check Anki connection status."""
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
        from anki.anki import check_anki_connection
        
        result = check_anki_connection.invoke({})
        
        return {
            "status": "connected" if "working" in result.lower() else "disconnected",
            "message": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking Anki connection: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@router.get("/anki/decks", response_model=dict)
async def get_anki_decks():
    """Get list of available Anki decks."""
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
        from anki.anki import get_anki_decks
        
        result = get_anki_decks.invoke({})
        
        return {
            "status": "success",
            "message": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error getting Anki decks: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@router.post("/sessions/{session_id}/cleanup", response_model=dict)
async def cleanup_session_data(session_id: str):
    """Cleanup session data and free resources."""
    try:
        # Deactivate session (force close)
        await session_manager.deactivate_session(session_id)
        
        # Clear conversation history
        await conversation_manager.clear_conversation(session_id)
        
        return {
            "message": "Session data cleaned up successfully",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.post("/maintenance/cleanup-inactive", response_model=dict)
async def cleanup_inactive_sessions(max_age_hours: int = 24):
    """Cleanup inactive sessions older than specified hours."""
    try:
        cleaned_count = await session_manager.cleanup_inactive_sessions(max_age_hours)
        
        return {
            "message": f"Cleaned up {cleaned_count} inactive sessions",
            "cleaned_sessions": cleaned_count,
            "max_age_hours": max_age_hours,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")