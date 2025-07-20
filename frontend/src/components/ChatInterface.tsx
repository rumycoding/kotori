import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  Alert,
  Snackbar,
  Fab,
  Tooltip,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  BugReport as DebugIcon,
  Assessment as AssessmentIcon,
  History as HistoryIcon,
} from '@mui/icons-material';

import { Message, StateInfo, ToolCall, KotoriConfig, UISettings } from '../types';
import { WebSocketService, webSocketManager } from '../services/websocket';
import MessageDisplay from './MessageDisplay';
import InputComponent from './InputComponent';
import AssessmentPanel from './AssessmentPanel';
import DebugPanel from './DebugPanel';
import ControlPanel from './ControlPanel';
import HistoryPanel from './HistoryPanel';

interface ChatInterfaceProps {
  sessionId: string;
  config: KotoriConfig;
  uiSettings: UISettings;
  onConfigChange: (config: KotoriConfig) => void;
  onUISettingsChange: (settings: UISettings) => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId,
  config,
  uiSettings,
  onConfigChange,
  onUISettingsChange,
}) => {
  // State management
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentState, setCurrentState] = useState<StateInfo>();
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [error, setError] = useState<string>('');
  const [showError, setShowError] = useState(false);
  
  // Track which messages have already been spoken to prevent double audio
  const spokenMessageIds = useRef<Set<string>>(new Set());

  // Helper function to add message without duplicates
  const addMessageSafely = (newMessage: Message) => {
    setMessages(prev => {
      // Check if message already exists by ID
      const existsById = prev.some(msg => msg.id === newMessage.id);
      if (existsById) {
        console.log(`Message with ID ${newMessage.id} already exists, skipping duplicate`);
        return prev;
      }
      
      // Additional check for very similar content to catch race conditions
      const normalizedNewContent = newMessage.content.trim().toLowerCase().replace(/[^\w\s]/g, '');
      const existsByContent = prev.some(msg => {
        if (msg.message_type !== newMessage.message_type) return false;
        const normalizedExistingContent = msg.content.trim().toLowerCase().replace(/[^\w\s]/g, '');
        
        // Check if contents are very similar (allowing for minor variations)
        return normalizedExistingContent === normalizedNewContent ||
               (normalizedExistingContent.length > 10 && normalizedNewContent.length > 10 &&
                (normalizedExistingContent.includes(normalizedNewContent) ||
                 normalizedNewContent.includes(normalizedExistingContent)));
      });
      
      if (existsByContent) {
        console.log(`Message with similar content already exists, skipping duplicate: ${newMessage.content.substring(0, 50)}...`);
        return prev;
      }
      
      return [...prev, newMessage];
    });
  };

  // Panel visibility states
  const [showSettings, setShowSettings] = useState(false);
  const [showDebug, setShowDebug] = useState(uiSettings.show_debug_panel);
  const [showAssessment, setShowAssessment] = useState(uiSettings.show_assessment);
  const [showHistory, setShowHistory] = useState(false);

  // WebSocket service
  const wsRef = useRef<WebSocketService>();

  // Initialize WebSocket connection
  useEffect(() => {
    // Don't try to connect if we don't have a session ID
    if (!sessionId || sessionId.trim() === '') {
      console.log('No session ID available, skipping WebSocket connection');
      setConnectionStatus('disconnected');
      return;
    }

    console.log('Initializing WebSocket connection for session:', sessionId);
    
    // Use the improved connection management
    setConnectionStatus('connecting');
    
    webSocketManager.ensureConnection(sessionId)
      .then((ws) => {
        // Only set up listeners if this is a new WebSocket instance for this component
        if (wsRef.current !== ws) {
          // Clean up previous listeners if we had a different WebSocket instance
          if (wsRef.current) {
            wsRef.current.off('ai_response', handleAIResponse);
            wsRef.current.off('state_change', handleStateChange);
            wsRef.current.off('tool_call', handleToolCall);
            wsRef.current.off('message_sent', handleMessageSent);
            wsRef.current.off('conversation_history', handleConversationHistory);
            wsRef.current.off('error', handleWebSocketError);
            wsRef.current.off('conversation_end', handleConversationEnd);
          }
          
          wsRef.current = ws;
          
          // Set up event listeners
          ws.on('ai_response', handleAIResponse);
          ws.on('state_change', handleStateChange);
          ws.on('tool_call', handleToolCall);
          ws.on('message_sent', handleMessageSent);
          ws.on('conversation_history', handleConversationHistory);
          ws.on('error', handleWebSocketError);
          ws.on('conversation_end', handleConversationEnd);
          
          // Request conversation history only for new connections
          ws.requestHistory();
        } else {
          console.log('Reusing existing WebSocket instance, skipping listener setup');
        }
        
        setConnectionStatus('connected');
        setError('');
      })
      .catch((err) => {
        console.error('WebSocket connection failed:', err);
        setConnectionStatus('error');
        setError('Failed to connect to chat service');
        setShowError(true);
      });

    // Cleanup on unmount
    return () => {
      if (wsRef.current) {
        wsRef.current.off('ai_response', handleAIResponse);
        wsRef.current.off('state_change', handleStateChange);
        wsRef.current.off('tool_call', handleToolCall);
        wsRef.current.off('message_sent', handleMessageSent);
        wsRef.current.off('conversation_history', handleConversationHistory);
        wsRef.current.off('error', handleWebSocketError);
        wsRef.current.off('conversation_end', handleConversationEnd);
        wsRef.current = undefined;
      }
    };
  }, [sessionId]);

  // Event handlers
  const handleAIResponse = (message: Message) => {
    addMessageSafely(message);
    setIsLoading(false);

    // Text-to-speech if enabled and message hasn't been spoken yet
    if (uiSettings.voice_settings.auto_play && !spokenMessageIds.current.has(message.id)) {
      spokenMessageIds.current.add(message.id);
      speakText(message.content);
    }
  };

  const handleStateChange = (stateInfo: StateInfo) => {
    setCurrentState(stateInfo);
  };

  const handleToolCall = (toolCall: ToolCall) => {
    setToolCalls(prev => [...prev, toolCall]);
  };


  const handleMessageSent = (message: Message) => {
    addMessageSafely(message);
  };

  const handleConversationHistory = (data: any) => {
    if (data.messages) {
      // Deduplicate messages by ID before setting
      const uniqueMessages = data.messages.reduce((acc: Message[], message: Message) => {
        const exists = acc.some(msg => msg.id === message.id);
        if (!exists) {
          acc.push(message);
          // Mark historical AI messages as already spoken to prevent auto-play on load
          if (message.message_type === 'ai') {
            spokenMessageIds.current.add(message.id);
          }
        }
        return acc;
      }, []);
      
      setMessages(uniqueMessages);
    }
  };

  const handleWebSocketError = (errorData: any) => {
    setError(errorData.message || 'WebSocket error occurred');
    setShowError(true);
    setConnectionStatus('error');
  };

  const handleConversationEnd = (data: any) => {
    setIsLoading(false);
    // Handle conversation end logic
  };

  const handleSendMessage = (messageText: string) => {
    if (!wsRef.current?.isConnected()) {
      setError('Not connected to chat service');
      setShowError(true);
      return;
    }

    setIsLoading(true);
    wsRef.current.sendMessage(messageText);
  };

  const speakText = (text: string) => {
    if ('speechSynthesis' in window) {
      // Cancel any currently speaking utterances to prevent overlap
      if (speechSynthesis.speaking) {
        speechSynthesis.cancel();
      }
      
      const utterance = new SpeechSynthesisUtterance(text);
      
      // Apply voice settings
      utterance.rate = uiSettings.voice_settings.rate;
      utterance.pitch = uiSettings.voice_settings.pitch;
      utterance.volume = uiSettings.voice_settings.volume;
      
      // Set voice if specified
      if (uiSettings.voice_settings.voice_name) {
        const voices = speechSynthesis.getVoices();
        const selectedVoice = voices.find(voice => voice.name === uiSettings.voice_settings.voice_name);
        if (selectedVoice) {
          utterance.voice = selectedVoice;
        }
      }

      speechSynthesis.speak(utterance);
    }
  };

  const handleExportHistory = async (format: 'json' | 'txt' | 'csv') => {
    try {
      // This would typically call the API service
      console.log(`Exporting history in ${format} format`);
    } catch (error) {
      setError('Failed to export conversation history');
      setShowError(true);
    }
  };

  const handleClearHistory = async () => {
    try {
      setMessages([]);
      setToolCalls([]);
      // Clear spoken message IDs when history is cleared
      spokenMessageIds.current.clear();
    } catch (error) {
      setError('Failed to clear conversation history');
      setShowError(true);
    }
  };

  const handleSearchHistory = (query: string): Message[] => {
    return messages.filter(msg => 
      msg.content.toLowerCase().includes(query.toLowerCase())
    );
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Container
        maxWidth="xl"
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          py: 2,
          overflow: 'auto',
          '&::-webkit-scrollbar': {
            width: '12px',
          },
          '&::-webkit-scrollbar-track': {
            background: '#f1f1f1',
            borderRadius: '6px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: '#888',
            borderRadius: '6px',
            '&:hover': {
              background: '#555',
            },
          },
          scrollBehavior: 'smooth',
        }}
      >
        <Grid container spacing={2} sx={{ flex: 1, minHeight: 0 }}>
        {/* Main Chat Area */}
        <Grid item xs={12} md={showAssessment || showDebug ? 8 : 12}>
          <Paper 
            elevation={2} 
            sx={{ 
              height: '100%', 
              display: 'flex', 
              flexDirection: 'column',
              position: 'relative'
            }}
          >
            {/* Connection Status */}
            {connectionStatus !== 'connected' && (
              <Box sx={{ p: 1, bgcolor: 'warning.light' }}>
                <Typography variant="caption" color="warning.contrastText">
                  Connection Status: {connectionStatus}
                </Typography>
              </Box>
            )}

            {/* Messages */}
            <Box sx={{ flex: 1, overflow: 'hidden' }}>
              <MessageDisplay 
                messages={messages} 
                isLoading={isLoading}
                onMessageClick={(msg) => console.log('Message clicked:', msg)}
              />
            </Box>

            {/* Input Area */}
            <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
              <InputComponent
                onSendMessage={handleSendMessage}
                disabled={connectionStatus !== 'connected' || isLoading}
                placeholder={config.language === 'japanese' ? 'メッセージを入力...' : 'Type your message...'}
                voiceEnabled={true}
                voiceSettings={uiSettings.voice_settings}
              />
            </Box>
          </Paper>
        </Grid>

        {/* Side Panels */}
        {(showAssessment || showDebug) && (
          <Grid item xs={12} md={4}>
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2, overflow: 'hidden' }}>
              {/* Assessment Panel */}
              {showAssessment && (
                <Box sx={{ flex: showDebug ? '1 1 50%' : '1 1 100%', minHeight: 0 }}>
                  <AssessmentPanel
                    assessmentHistory={currentState?.assessment_history}
                    isVisible={showAssessment}
                    onToggleVisibility={() => setShowAssessment(!showAssessment)}
                  />
                </Box>
              )}

              {/* Debug Panel */}
              {showDebug && (
                <Box sx={{ flex: showAssessment ? '1 1 50%' : '1 1 100%', minHeight: 0 }}>
                  <DebugPanel
                    stateInfo={currentState}
                    toolCalls={toolCalls}
                    isVisible={showDebug}
                    onToggleVisibility={() => setShowDebug(!showDebug)}
                  />
                </Box>
              )}
            </Box>
          </Grid>
        )}
        </Grid>

      {/* Floating Action Buttons */}
      <Box sx={{ position: 'fixed', bottom: 16, right: 16, display: 'flex', flexDirection: 'column', gap: 1 }}>
        <Tooltip title="Settings">
          <span>
            <Fab size="small" onClick={() => setShowSettings(!showSettings)}>
              <SettingsIcon />
            </Fab>
          </span>
        </Tooltip>
        
        <Tooltip title="Assessment">
          <span>
            <Fab
              size="small"
              color={showAssessment ? 'primary' : 'default'}
              onClick={() => setShowAssessment(!showAssessment)}
            >
              <AssessmentIcon />
            </Fab>
          </span>
        </Tooltip>
        
        <Tooltip title="Debug">
          <span>
            <Fab
              size="small"
              color={showDebug ? 'primary' : 'default'}
              onClick={() => setShowDebug(!showDebug)}
            >
              <DebugIcon />
            </Fab>
          </span>
        </Tooltip>
        
        <Tooltip title="History">
          <span>
            <Fab
              size="small"
              color={showHistory ? 'primary' : 'default'}
              onClick={() => setShowHistory(!showHistory)}
            >
              <HistoryIcon />
            </Fab>
          </span>
        </Tooltip>
      </Box>

      {/* Control Panel Dialog */}
      <ControlPanel
        voiceSettings={uiSettings.voice_settings}
        uiSettings={uiSettings}
        onVoiceSettingsChange={(settings) => 
          onUISettingsChange({ ...uiSettings, voice_settings: settings })
        }
        onUISettingsChange={onUISettingsChange}
        open={showSettings}
        onClose={() => setShowSettings(false)}
      />

      {/* History Panel Dialog */}
      <HistoryPanel
        messages={messages}
        onExport={handleExportHistory}
        onClear={handleClearHistory}
        onSearch={handleSearchHistory}
        isVisible={showHistory}
        onToggleVisibility={() => setShowHistory(!showHistory)}
      />

      {/* Error Snackbar */}
      <Snackbar
        open={showError}
        autoHideDuration={6000}
        onClose={() => setShowError(false)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert 
          onClose={() => setShowError(false)} 
          severity="error"
          variant="filled"
        >
          {error}
        </Alert>
      </Snackbar>
      </Container>
    </Box>
  );
};

export default ChatInterface;