import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from ..models import SessionState, KotoriConfig, UISettings, StateInfo, Message, MessageType

class SessionManager:
    """Manages chat sessions and their state."""
    
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        self._creation_lock = asyncio.Lock()  # Global lock for session creation
        self._creating_sessions: set = set()  # Track sessions being created
        
    async def create_session(self, config: Optional[KotoriConfig] = None) -> str:
        """Create a new chat session with protection against duplicate creation."""
        async with self._creation_lock:
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Double-check uniqueness (extremely rare UUID collision protection)
            while session_id in self.sessions or session_id in self._creating_sessions:
                session_id = str(uuid.uuid4())
            
            # Mark session as being created
            self._creating_sessions.add(session_id)
            
            try:
                if config is None:
                    config = KotoriConfig()
                    
                session_state = SessionState(
                    session_id=session_id,
                    config=config,
                    ui_settings=UISettings()
                )
                
                # Create the session atomically
                self.sessions[session_id] = session_state
                self.session_locks[session_id] = asyncio.Lock()
                
                print(f"✓ Session created successfully: {session_id}")
                return session_id
                
            finally:
                # Remove from creating set
                self._creating_sessions.discard(session_id)
    
    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session state by ID."""
        session = self.sessions.get(session_id)
        if session:
            print(f"✓ Session found: {session_id} (active: {session.is_active})")
        else:
            print(f"✗ Session not found: {session_id}")
        return session
    
    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return session_id in self.sessions
    
    async def get_session_count(self) -> int:
        """Get total number of sessions."""
        return len(self.sessions)
    
    async def get_active_session_count(self) -> int:
        """Get number of active sessions."""
        return len([s for s in self.sessions.values() if s.is_active])
    
    async def update_session_activity(self, session_id: str):
        """Update last activity timestamp for a session."""
        if session_id in self.sessions:
            self.sessions[session_id].last_activity = datetime.now()
    
    async def update_session_config(self, session_id: str, config: KotoriConfig) -> bool:
        """Update session configuration."""
        if session_id not in self.sessions:
            return False
            
        async with self.session_locks[session_id]:
            self.sessions[session_id].config = config
            await self.update_session_activity(session_id)
            
        return True
    
    async def update_ui_settings(self, session_id: str, ui_settings: UISettings) -> bool:
        """Update UI settings for a session."""
        if session_id not in self.sessions:
            return False
            
        async with self.session_locks[session_id]:
            self.sessions[session_id].ui_settings = ui_settings
            await self.update_session_activity(session_id)
            
        return True
    
    async def update_state_info(self, session_id: str, state_info: StateInfo) -> bool:
        """Update current state information."""
        if session_id not in self.sessions:
            return False
            
        async with self.session_locks[session_id]:
            self.sessions[session_id].current_state = state_info
            await self.update_session_activity(session_id)
            
        return True
    
    async def close_session(self, session_id: str, force: bool = False) -> bool:
        """Close and cleanup a session."""
        if session_id not in self.sessions:
            return False
            
        async with self.session_locks[session_id]:
            if force:
                # Only mark as inactive if explicitly forced (e.g., user logout)
                self.sessions[session_id].is_active = False
                print(f"✓ Session {session_id} forcefully closed")
            else:
                # For normal disconnections, keep session active for reconnection
                print(f"✓ Session {session_id} connection closed but kept active for reconnection")
            
        return True
    
    async def deactivate_session(self, session_id: str) -> bool:
        """Deactivate a session (for explicit closure)."""
        if session_id not in self.sessions:
            return False
            
        async with self.session_locks[session_id]:
            self.sessions[session_id].is_active = False
            print(f"✓ Session {session_id} deactivated")
            
        return True
    
    async def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return [
            session_id for session_id, session in self.sessions.items()
            if session.is_active
        ]
    
    async def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """Clean up old inactive sessions."""
        current_time = datetime.now()
        to_remove = []
        
        for session_id, session in self.sessions.items():
            if not session.is_active:
                age_hours = (current_time - session.last_activity).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(session_id)
        
        for session_id in to_remove:
            if session_id in self.sessions:
                del self.sessions[session_id]
            if session_id in self.session_locks:
                del self.session_locks[session_id]
        
        return len(to_remove)


class ConversationManager:
    """Manages conversation history for sessions."""
    
    def __init__(self):
        self.conversations: Dict[str, List[Message]] = {}
        self.conversation_locks: Dict[str, asyncio.Lock] = {}
    
    async def add_message(self, session_id: str, message: Message):
        """Add a message to the conversation history with duplicate prevention."""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
            self.conversation_locks[session_id] = asyncio.Lock()
        
        async with self.conversation_locks[session_id]:
            # Check for duplicate messages by ID first
            existing_messages = self.conversations[session_id]
            if any(msg.id == message.id for msg in existing_messages):
                print(f"Duplicate message ID detected in conversation history: {message.id}")
                return
            
            # Additional check for very similar content within the last few messages
            # Only check the last 5 messages to avoid performance issues
            recent_messages = existing_messages[-5:] if len(existing_messages) > 5 else existing_messages
            normalized_new_content = message.content.strip().lower()
            
            for recent_msg in recent_messages:
                if (recent_msg.message_type == message.message_type and
                    recent_msg.content.strip().lower() == normalized_new_content):
                    print(f"Duplicate message content detected in conversation history: {message.content[:50]}...")
                    return
            
            self.conversations[session_id].append(message)
    
    async def get_conversation(self, session_id: str) -> List[Message]:
        """Get conversation history for a session."""
        return self.conversations.get(session_id, [])
    
    async def get_recent_messages(self, session_id: str, limit: int = 10) -> List[Message]:
        """Get recent messages from conversation."""
        messages = self.conversations.get(session_id, [])
        return messages[-limit:] if len(messages) > limit else messages
    
    async def clear_conversation(self, session_id: str) -> bool:
        """Clear conversation history for a session."""
        if session_id in self.conversations:
            async with self.conversation_locks[session_id]:
                self.conversations[session_id] = []
            return True
        return False
    
    async def export_conversation(self, session_id: str, format: str = "json") -> Optional[str]:
        """Export conversation in specified format."""
        messages = self.conversations.get(session_id, [])
        
        if format == "json":
            import json
            return json.dumps([msg.model_dump() for msg in messages], indent=2, default=str)
        elif format == "txt":
            lines = []
            for msg in messages:
                timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                lines.append(f"[{timestamp}] {msg.message_type.upper()}: {msg.content}")
            return "\n".join(lines)
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["timestamp", "type", "content", "metadata"])
            for msg in messages:
                writer.writerow([
                    msg.timestamp.isoformat(),
                    msg.message_type.value,
                    msg.content,
                    str(msg.metadata) if msg.metadata else ""
                ])
            return output.getvalue()
        
        return None


# Global instances
session_manager = SessionManager()
conversation_manager = ConversationManager()