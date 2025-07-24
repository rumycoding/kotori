import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from langchain_openai import AzureChatOpenAI

from ..models import (
    WebSocketEvent, Message, MessageType, KotoriConfig, 
    StateInfo, ToolCall, AssessmentMetrics
)
from ..services.session_manager import session_manager, conversation_manager
from ..services.kotori_adapter import KotoriBotAdapter


class WebSocketConnectionManager:
    """Manages WebSocket connections for chat sessions."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_adapters: Dict[str, KotoriBotAdapter] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept WebSocket connection and setup session."""
        print(f"Accepting WebSocket connection for session: {session_id}")
        
        # Validate session_id format
        if not session_id or len(session_id.strip()) == 0:
            print(f"✗ Invalid session ID: '{session_id}'")
            await websocket.close(code=1008, reason="Invalid session ID")
            return
        
        # Check for existing active connection
        if session_id in self.active_connections:
            print(f"✗ Session {session_id} already has an active WebSocket connection")
            await websocket.close(code=1008, reason="Session already connected")
            return
        
        try:
            await websocket.accept()
            print(f"✓ WebSocket connection accepted for session: {session_id}")
            self.active_connections[session_id] = websocket
        except Exception as e:
            print(f"✗ Failed to accept WebSocket connection for session {session_id}: {e}")
            raise
        
        # Get existing session (don't create new ones here)
        session = await session_manager.get_session(session_id)
        if session is None:
            print(f"✗ Session {session_id} not found. This session should have been created via REST API first.")
            # Send error to client that session doesn't exist
            await self.send_event(session_id, "error", {
                "error": f"Session {session_id} not found. Please create a session first.",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })
            # Close the connection since session doesn't exist
            await websocket.close(code=1008, reason="Session not found")
            return
        
        # For reconnections, reactivate inactive sessions if they exist
        if not session.is_active:
            print(f"⚠ Session {session_id} is inactive, reactivating for reconnection")
            # Reactivate the session for reconnection
            session.is_active = True
            await session_manager.update_session_activity(session_id)
            print(f"✓ Session {session_id} reactivated")
        
        # Check for existing adapter (prevent duplicate setup)
        if session_id in self.session_adapters:
            print(f"⚠ Session {session_id} already has an adapter - cleaning up old adapter")
            await self.session_adapters[session_id].stop_conversation()
            del self.session_adapters[session_id]
        
        # Setup KotoriBot adapter with existing session
        await self._setup_kotori_adapter(session_id, session.config)
        
        # Send initial connection confirmation
        await self.send_event(session_id, "connection_established", {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "config": session.config.model_dump() if session.config else None
        })
        
        print(f"✓ WebSocket connection fully established for session: {session_id}")
    
    async def disconnect(self, session_id: str, force_close: bool = False):
        """Handle WebSocket disconnection."""
        print(f"Disconnecting WebSocket for session: {session_id} (force_close: {force_close})")
        
        # Remove active connection
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"✓ Removed active connection for session: {session_id}")
        
        # Stop and remove adapter (but keep session active for reconnection)
        if session_id in self.session_adapters:
            try:
                await self.session_adapters[session_id].stop_conversation()
                del self.session_adapters[session_id]
                print(f"✓ Stopped and removed adapter for session: {session_id}")
            except Exception as e:
                print(f"⚠ Error stopping adapter for session {session_id}: {e}")
        
        # Only close session if explicitly requested (not for normal disconnections)
        if force_close:
            try:
                await session_manager.close_session(session_id, force=True)
                print(f"✓ Session {session_id} forcefully closed")
            except Exception as e:
                print(f"⚠ Error closing session {session_id}: {e}")
        else:
            # For normal disconnections, keep session active for reconnection
            try:
                await session_manager.close_session(session_id, force=False)
                print(f"✓ Session {session_id} connection closed but kept active for reconnection")
            except Exception as e:
                print(f"⚠ Error handling session {session_id} disconnection: {e}")
    
    async def _setup_kotori_adapter(self, session_id: str, config: KotoriConfig):
        """Setup KotoriBot adapter for the session."""
        # Get LLM configuration from environment
        import os
        from pydantic import SecretStr
        
        llm = AzureChatOpenAI(
            model=os.environ["AZURE_MODEL_NAME"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            api_key=SecretStr(os.environ["AZURE_OPENAI_API_KEY"])
        )
        
        # Create adapter
        adapter_config = {
            "language": config.language,
            "deck_name": config.deck_name,
            "temperature": config.temperature
        }
        
        adapter = KotoriBotAdapter(llm, adapter_config)
        self.session_adapters[session_id] = adapter
        
        # Register callbacks for real-time updates
        adapter.register_callback("ai_response",
            lambda msg: self._handle_ai_response(session_id, msg))
        adapter.register_callback("user_message",
            lambda msg: self._handle_user_message(session_id, msg))
        adapter.register_callback("state_change",
            lambda state: self._handle_state_change(session_id, state))
        adapter.register_callback("tool_call",
            lambda tool: self._handle_tool_call(session_id, tool))
        adapter.register_callback("tool_message",
            lambda msg: self._handle_tool_message(session_id, msg))
        adapter.register_callback("assessment_update",
            lambda metrics: self._handle_assessment_update(session_id, metrics))
        adapter.register_callback("conversation_end",
            lambda data: self._handle_conversation_end(session_id, data))
        adapter.register_callback("error",
            lambda error: self._handle_error(session_id, error))
        
        # Start conversation with error handling
        try:
            await adapter.start_conversation()
        except Exception as e:
            print(f"Warning: Failed to start conversation for session {session_id}: {e}")
            # Don't fail the WebSocket connection, just log the error
            # The conversation can be started later when the user sends a message
    
    async def _handle_ai_response(self, session_id: str, message: Message):
        """Handle AI response from KotoriBot."""
        # Add to conversation history
        await conversation_manager.add_message(session_id, message)
        
        # Add a small delay to prevent rapid-fire duplicate sends
        # This helps prevent race conditions in the frontend
        await asyncio.sleep(0.1)
        
        # Send to frontend
        await self.send_event(session_id, "ai_response", {
            "message": message.model_dump(),
            "session_id": session_id
        })
    
    async def _handle_user_message(self, session_id: str, message: Message):
        """Handle user message."""
        # Add to conversation history
        await conversation_manager.add_message(session_id, message)
        
        # Update session activity
        await session_manager.update_session_activity(session_id)
    
    async def _handle_state_change(self, session_id: str, state_info: StateInfo):
        """Handle state changes from KotoriBot."""
        # Update session state
        await session_manager.update_state_info(session_id, state_info)
        
        # Send to frontend
        await self.send_event(session_id, "state_change", {
            "state": state_info.model_dump(),
            "session_id": session_id
        })
    
    async def _handle_tool_call(self, session_id: str, tool_call: ToolCall):
        """Handle tool calls from KotoriBot."""
        print(f"=== WEBSOCKET HANDLING TOOL CALL ===")
        print(f"Session ID: {session_id}")
        print(f"Tool call object: {tool_call}")
        print(f"Tool call model_dump: {tool_call.model_dump()}")
        
        # Send to frontend
        await self.send_event(session_id, "tool_call", {
            "tool": tool_call.model_dump(),
            "session_id": session_id
        })
        print(f"Tool call event sent to frontend")
        print(f"===================================")
    
    async def _handle_tool_message(self, session_id: str, message: Message):
        """Handle tool messages from KotoriBot."""
        print(f"=== WEBSOCKET HANDLING TOOL MESSAGE ===")
        print(f"Session ID: {session_id}")
        print(f"Tool message: {message}")
        print(f"Tool calls in message: {message.tool_calls}")
        
        # Add to conversation history
        await conversation_manager.add_message(session_id, message)
        
        # Send to frontend as a regular message
        await self.send_event(session_id, "ai_response", {
            "message": message.model_dump(),
            "session_id": session_id
        })
        print(f"Tool message sent to frontend")
        print(f"=====================================")
    
    async def _handle_assessment_update(self, session_id: str, metrics: AssessmentMetrics):
        """Handle assessment updates."""
        # Send to frontend
        await self.send_event(session_id, "assessment_update", {
            "metrics": metrics.model_dump(),
            "session_id": session_id
        })
    
    async def _handle_conversation_end(self, session_id: str, data: Dict[str, Any]):
        """Handle conversation end."""
        await self.send_event(session_id, "conversation_end", {
            "data": data,
            "session_id": session_id
        })
    
    async def _handle_error(self, session_id: str, error: Dict[str, Any]):
        """Handle errors from KotoriBot."""
        await self.send_event(session_id, "error", {
            "error": error,
            "session_id": session_id
        })
    
    async def send_event(self, session_id: str, event_type: str, data: Dict[str, Any]):
        """Send event to specific session."""
        if session_id in self.active_connections:
            event = WebSocketEvent(
                event_type=event_type,
                data=data,
                session_id=session_id
            )
            
            try:
                await self.active_connections[session_id].send_text(
                    json.dumps(event.model_dump(), default=str)
                )
            except Exception as e:
                print(f"Error sending WebSocket message to {session_id}: {e}")
                # Connection might be broken, remove it
                await self.disconnect(session_id)
    
    async def handle_user_message(self, session_id: str, message: str):
        """Handle incoming user message."""
        if session_id in self.session_adapters:
            # Create user message
            user_message = Message(
                id=str(uuid.uuid4()),
                content=message,
                message_type=MessageType.USER,
                timestamp=datetime.now(),
                tool_calls=None
            )
            
            # Send to KotoriBot
            success = await self.session_adapters[session_id].send_user_message(message)
            
            if success:
                # Add to conversation history
                await conversation_manager.add_message(session_id, user_message)
                
                # Send confirmation to frontend
                await self.send_event(session_id, "message_sent", {
                    "message": user_message.model_dump(),
                    "session_id": session_id
                })
            else:
                # Send error
                await self.send_event(session_id, "error", {
                    "error": "Failed to send message - bot might not be waiting for input",
                    "session_id": session_id
                })
    
    async def get_conversation_history(self, session_id: str) -> Dict[str, Any]:
        """Get conversation history for a session."""
        messages = await conversation_manager.get_conversation(session_id)
        session = await session_manager.get_session(session_id)
        
        return {
            "session_id": session_id,
            "messages": [msg.model_dump() for msg in messages],
            "session_info": session.model_dump() if session else None
        }


# Global connection manager instance
connection_manager = WebSocketConnectionManager()


async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Main WebSocket endpoint handler."""
    try:
        await connection_manager.connect(websocket, session_id)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                event_type = message_data.get("event_type")
                payload = message_data.get("data", {})
                
                if event_type == "user_message":
                    message_content = payload.get("message", "")
                    await connection_manager.handle_user_message(session_id, message_content)
                
                elif event_type == "get_history":
                    history = await connection_manager.get_conversation_history(session_id)
                    await connection_manager.send_event(session_id, "conversation_history", history)
                
                elif event_type == "ping":
                    await connection_manager.send_event(session_id, "pong", {"timestamp": datetime.now().isoformat()})
                
                else:
                    await connection_manager.send_event(session_id, "error", {
                        "error": f"Unknown event type: {event_type}",
                        "session_id": session_id
                    })
                    
            except json.JSONDecodeError:
                await connection_manager.send_event(session_id, "error", {
                    "error": "Invalid JSON format",
                    "session_id": session_id
                })
            except Exception as e:
                await connection_manager.send_event(session_id, "error", {
                    "error": f"Error processing message: {str(e)}",
                    "session_id": session_id
                })
                
    except WebSocketDisconnect:
        await connection_manager.disconnect(session_id)
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
        await connection_manager.disconnect(session_id)