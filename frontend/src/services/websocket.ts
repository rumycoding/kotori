import { WebSocketEvent, WebSocketEventType, Message, StateInfo, ToolCall, AssessmentMetrics } from '../types';

export type WebSocketCallback = (data: any) => void;

export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private sessionId: string;
  private callbacks: Map<WebSocketEventType, WebSocketCallback[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isManuallyDisconnected = false;

  constructor(sessionId: string, baseUrl?: string) {
    console.log('WebSocket service created for session ID:', sessionId);
    this.sessionId = sessionId;
    
    // Automatically determine WebSocket base URL if not provided
    if (!baseUrl) {
      // Check for dedicated WebSocket URL first
      const wsUrl = process.env.REACT_APP_WEBSOCKET_URL;
      
      if (wsUrl) {
        baseUrl = wsUrl;
        console.log('WebSocket URL from environment:', baseUrl);
      } else {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        
        // Check multiple possible sources for the API URL
        const apiUrl = process.env.REACT_APP_API_URL ||
                       (window as any)?.env?.REACT_APP_API_URL ||
                       'http://localhost:8000/api';
        
        console.log('API URL found:', apiUrl);
        
        // Extract base URL from API URL
        let apiBaseUrl;
        try {
          const url = new URL(apiUrl);
          apiBaseUrl = url.host;
        } catch {
          // Fallback parsing
          apiBaseUrl = apiUrl.replace('/api', '').replace('http://', '').replace('https://', '');
        }
        
        // For development, always use localhost:8000 if we detect we're in development
        if (process.env.NODE_ENV === 'development' || window.location.hostname === 'localhost') {
          apiBaseUrl = 'localhost:8000';
        }
        
        baseUrl = `${protocol}//${apiBaseUrl}`;
        console.log('WebSocket base URL determined:', baseUrl);
      }
    }
    
    this.url = `${baseUrl}/ws/chat/${sessionId}`;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        console.log(`Attempting WebSocket connection to: ${this.url}`);
        this.ws = new WebSocket(this.url);
        this.isManuallyDisconnected = false;

        this.ws.onopen = () => {
          console.log(`WebSocket connected successfully to: ${this.url}`);
          this.reconnectAttempts = 0;
          this.emit('connection_established', { sessionId: this.sessionId });
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data: WebSocketEvent = JSON.parse(event.data);
            this.handleIncomingMessage(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket connection closed:', event.code, event.reason);
          this.ws = null;
          
          if (!this.isManuallyDisconnected && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          } else {
            this.emit('error', {
              type: 'connection',
              message: 'WebSocket connection lost',
              timestamp: new Date().toISOString()
            });
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          console.error('WebSocket URL:', this.url);
          console.error('WebSocket readyState:', this.ws?.readyState);
          this.emit('error', {
            type: 'connection',
            message: `WebSocket connection error to ${this.url}`,
            timestamp: new Date().toISOString(),
            details: error
          });
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect(): void {
    this.isManuallyDisconnected = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      if (!this.isManuallyDisconnected) {
        this.connect().catch(console.error);
      }
    }, delay);
  }

  private handleIncomingMessage(event: WebSocketEvent): void {
    const { event_type, data } = event;
    
    switch (event_type) {
      case 'ai_response':
        this.emit('ai_response', data.message as Message);
        break;
      case 'state_change':
        this.emit('state_change', data.state as StateInfo);
        break;
      case 'tool_call':
        console.log('=== WEBSOCKET TOOL_CALL EVENT ===');
        console.log('Raw tool call data:', data);
        console.log('Tool object:', data.tool);
        this.emit('tool_call', data.tool as ToolCall);
        console.log('=================================');
        break;
      case 'assessment_update':
        this.emit('assessment_update', data.metrics as AssessmentMetrics);
        break;
      case 'conversation_history':
        this.emit('conversation_history', data);
        break;
      case 'message_sent':
        this.emit('message_sent', data.message as Message);
        break;
      case 'conversation_end':
        this.emit('conversation_end', data);
        break;
      case 'error':
        this.emit('error', data);
        break;
      case 'pong':
        this.emit('pong', data);
        break;
      case 'connection_established':
        this.emit('connection_established', data);
        break;
      default:
        console.log('Unhandled WebSocket event:', event_type, data);
    }
  }

  sendMessage(message: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const event = {
        event_type: 'user_message',
        data: {
          message,
          session_id: this.sessionId,
          timestamp: new Date().toISOString()
        }
      };
      
      this.ws.send(JSON.stringify(event));
    } else {
      console.error('WebSocket is not connected');
      this.emit('error', {
        type: 'message',
        message: 'Cannot send message - not connected',
        timestamp: new Date().toISOString()
      });
    }
  }

  requestHistory(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const event = {
        event_type: 'get_history',
        data: { session_id: this.sessionId }
      };
      
      this.ws.send(JSON.stringify(event));
    }
  }

  ping(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const event = {
        event_type: 'ping',
        data: { timestamp: new Date().toISOString() }
      };
      
      this.ws.send(JSON.stringify(event));
    }
  }

  on(eventType: WebSocketEventType, callback: WebSocketCallback): void {
    if (!this.callbacks.has(eventType)) {
      this.callbacks.set(eventType, []);
    }
    this.callbacks.get(eventType)!.push(callback);
  }

  off(eventType: WebSocketEventType, callback: WebSocketCallback): void {
    const callbacks = this.callbacks.get(eventType);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  private emit(eventType: WebSocketEventType, data: any): void {
    const callbacks = this.callbacks.get(eventType);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in WebSocket callback for ${eventType}:`, error);
        }
      });
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getConnectionState(): string {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'disconnecting';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }
}

// Singleton instance manager
class WebSocketManager {
  private instances: Map<string, WebSocketService> = new Map();
  private connectionPromises: Map<string, Promise<void>> = new Map();

  getInstance(sessionId: string, baseUrl?: string): WebSocketService {
    if (!this.instances.has(sessionId)) {
      console.log('Creating new WebSocket service instance for session:', sessionId);
      this.instances.set(sessionId, new WebSocketService(sessionId, baseUrl));
    } else {
      console.log('Reusing existing WebSocket service instance for session:', sessionId);
    }
    return this.instances.get(sessionId)!;
  }

  async ensureConnection(sessionId: string, baseUrl?: string): Promise<WebSocketService> {
    const instance = this.getInstance(sessionId, baseUrl);
    
    // If already connected, return immediately
    if (instance.isConnected()) {
      console.log('WebSocket already connected for session:', sessionId);
      return instance;
    }
    
    // If connection is in progress, wait for it
    if (this.connectionPromises.has(sessionId)) {
      console.log('WebSocket connection already in progress for session:', sessionId);
      try {
        await this.connectionPromises.get(sessionId);
        return instance;
      } catch (error) {
        console.error('Failed to wait for existing connection:', error);
        // Remove failed promise and try again
        this.connectionPromises.delete(sessionId);
      }
    }
    
    // Start new connection
    console.log('Starting new WebSocket connection for session:', sessionId);
    const connectionPromise = instance.connect().finally(() => {
      this.connectionPromises.delete(sessionId);
    });
    
    this.connectionPromises.set(sessionId, connectionPromise);
    await connectionPromise;
    
    return instance;
  }

  removeInstance(sessionId: string): void {
    const instance = this.instances.get(sessionId);
    if (instance) {
      instance.disconnect();
      this.instances.delete(sessionId);
    }
    this.connectionPromises.delete(sessionId);
  }

  disconnectAll(): void {
    this.instances.forEach((instance, sessionId) => {
      instance.disconnect();
    });
    this.instances.clear();
    this.connectionPromises.clear();
  }
}

export const webSocketManager = new WebSocketManager();