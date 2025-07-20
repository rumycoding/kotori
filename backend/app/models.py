from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class MessageType(str, Enum):
    USER = "user"
    AI = "ai" 
    SYSTEM = "system"
    TOOL = "tool"

class Message(BaseModel):
    id: str
    content: str
    message_type: MessageType
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class ChatMessage(BaseModel):
    message: str
    session_id: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)

class KotoriConfig(BaseModel):
    language: str = Field(default="english", description="Language for learning (english/japanese)")
    deck_name: Optional[str] = Field(default="Kotori", description="Name of the Anki deck")
    
class SessionConfig(BaseModel):
    session_id: str
    config: KotoriConfig
    
class AssessmentMetrics(BaseModel):
    active_vocabulary_usage: Optional[int] = None
    comprehension_depth: Optional[int] = None
    contextual_application: Optional[int] = None
    retention_indicators: Optional[int] = None
    overall_mastery: Optional[int] = None
    next_steps: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class StateInfo(BaseModel):
    current_node: str
    next_node: Optional[str] = None
    learning_goals: Optional[str] = None
    active_cards: Optional[str] = None
    assessment_history: Optional[str] = None
    counter: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

class ToolCall(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]
    status: str  # "pending", "success", "error"
    result: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class WebSocketEvent(BaseModel):
    event_type: str
    data: Dict[str, Any]
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ConversationHistory(BaseModel):
    session_id: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    config: KotoriConfig

class ExportRequest(BaseModel):
    session_id: str
    format: str = Field(default="json", description="Export format (json, csv, txt)")
    include_metadata: bool = Field(default=True)

class VoiceSettings(BaseModel):
    voice_name: Optional[str] = None
    rate: float = Field(default=1.0, ge=0.1, le=2.0)
    pitch: float = Field(default=1.0, ge=0.0, le=2.0)
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    auto_play: bool = Field(default=True)

class UISettings(BaseModel):
    theme: str = Field(default="light", description="UI theme (light/dark)")
    debug_mode: bool = Field(default=False)
    show_assessment: bool = Field(default=True)
    show_debug_panel: bool = Field(default=False)
    voice_settings: VoiceSettings = Field(default_factory=VoiceSettings)

class SessionState(BaseModel):
    session_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    config: KotoriConfig = Field(default_factory=KotoriConfig)
    ui_settings: UISettings = Field(default_factory=UISettings)
    current_state: Optional[StateInfo] = None

class GraphNode(BaseModel):
    id: str
    name: str
    type: str
    is_current: bool = False
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None
    is_active: bool = False

class StateGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    current_node: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, str] = Field(default_factory=dict)