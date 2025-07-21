export interface Message {
  id: string;
  content: string;
  message_type: 'user' | 'ai' | 'system' | 'tool';
  timestamp: string;
  metadata?: Record<string, any>;
  tool_calls?: ToolCall[];
}

export interface KotoriConfig {
  language: string;
  deck_name?: string;
}

export interface UISettings {
  theme: 'light' | 'dark';
  debug_mode: boolean;
  show_assessment: boolean;
  show_debug_panel: boolean;
  voice_settings: VoiceSettings;
}

export interface VoiceSettings {
  voice_name?: string;
  rate: number;
  pitch: number;
  volume: number;
  auto_play: boolean;
}

export interface StateInfo {
  current_node: string;
  next_node?: string;
  learning_goals?: string;
  active_cards?: string;
  assessment_history?: string[];
  counter: number;
  timestamp: string;
}

export interface ToolCall {
  tool_name: string;
  parameters: Record<string, any>;
  status: 'pending' | 'success' | 'error';
  result?: string;
  timestamp: string;
}

export interface AssessmentMetrics {
  active_vocabulary_usage?: number;
  comprehension_depth?: number;
  contextual_application?: number;
  retention_indicators?: number;
  overall_mastery?: number;
  next_steps?: string;
  timestamp: string;
}

export interface WebSocketEvent {
  event_type: string;
  data: Record<string, any>;
  session_id: string;
  timestamp: string;
}

export interface SessionState {
  session_id: string;
  is_active: boolean;
  created_at: string;
  last_activity: string;
  config: KotoriConfig;
  ui_settings: UISettings;
  current_state?: StateInfo;
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  is_current: boolean;
  position: { x: number; y: number };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  is_active: boolean;
}

export interface StateGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  current_node?: string;
}

export interface ConversationHistory {
  session_id: string;
  messages: Message[];
  message_count: number;
  session_info?: SessionState;
  timestamp: string;
}

export interface ApiResponse<T = any> {
  status?: string;
  message?: string;
  data?: T;
  timestamp: string;
}

export interface HealthStatus {
  status: string;
  services: Record<string, string>;
  timestamp: string;
}

// WebSocket event types
export type WebSocketEventType = 
  | 'connection_established'
  | 'user_message'
  | 'ai_response'
  | 'state_change'
  | 'tool_call'
  | 'assessment_update'
  | 'conversation_end'
  | 'error'
  | 'message_sent'
  | 'conversation_history'
  | 'ping'
  | 'pong';

// Speech recognition types
export interface SpeechRecognitionResult {
  transcript: string;
  confidence: number;
  isFinal: boolean;
}

export interface SpeechSynthesisOptions {
  text: string;
  voice?: SpeechSynthesisVoice;
  rate?: number;
  pitch?: number;
  volume?: number;
}

// Component props
export interface ChatInterfaceProps {
  sessionId: string;
  config: KotoriConfig;
  uiSettings: UISettings;
  onConfigChange: (config: KotoriConfig) => void;
  onUISettingsChange: (settings: UISettings) => void;
}

export interface MessageDisplayProps {
  messages: Message[];
  isLoading?: boolean;
  onMessageClick?: (message: Message) => void;
}

export interface InputComponentProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  voiceEnabled?: boolean;
  voiceSettings?: VoiceSettings;
}

export interface AssessmentPanelProps {
  assessmentHistory?: string[];
  isVisible: boolean;
  onToggleVisibility: () => void;
}

export interface DebugPanelProps {
  stateInfo?: StateInfo;
  toolCalls: ToolCall[];
  messages?: Message[];
  stateGraph?: StateGraph;
  isVisible: boolean;
  onToggleVisibility: () => void;
}

export interface ControlPanelProps {
  voiceSettings: VoiceSettings;
  uiSettings: UISettings;
  onVoiceSettingsChange: (settings: VoiceSettings) => void;
  onUISettingsChange: (settings: UISettings) => void;
}

export interface HistoryPanelProps {
  messages: Message[];
  onExport: (format: 'json' | 'txt' | 'csv') => void;
  onClear: () => void;
  onSearch: (query: string) => Message[];
  isVisible: boolean;
  onToggleVisibility: () => void;
}

// Error types
export interface ApiError {
  error: string;
  message: string;
  timestamp: string;
}

export interface WebSocketError {
  type: 'connection' | 'message' | 'timeout';
  message: string;
  timestamp: string;
}

// Theme types
export interface ThemeConfig {
  palette: {
    mode: 'light' | 'dark';
    primary: {
      main: string;
      light: string;
      dark: string;
    };
    secondary: {
      main: string;
      light: string;
      dark: string;
    };
    background: {
      default: string;
      paper: string;
    };
    text: {
      primary: string;
      secondary: string;
    };
  };
  typography: {
    fontFamily: string;
    fontSize: number;
  };
  spacing: (factor: number) => number;
}

// Context types
export interface AppContextType {
  sessionId: string;
  config: KotoriConfig;
  uiSettings: UISettings;
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  updateConfig: (config: Partial<KotoriConfig>) => void;
  updateUISettings: (settings: Partial<UISettings>) => void;
  createNewSession: () => Promise<void>;
  reconnect: () => void;
}

export interface ChatContextType {
  messages: Message[];
  currentState?: StateInfo;
  assessmentMetrics?: AssessmentMetrics;
  assessmentHistory: AssessmentMetrics[];
  toolCalls: ToolCall[];
  isLoading: boolean;
  sendMessage: (message: string) => void;
  clearHistory: () => void;
  exportHistory: (format: 'json' | 'txt' | 'csv') => Promise<string>;
}