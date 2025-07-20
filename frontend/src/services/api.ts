import { KotoriConfig, UISettings, ApiResponse, HealthStatus, SessionState, ConversationHistory } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || (window as any)?.env?.REACT_APP_API_URL || 'http://localhost:8000/api';

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorData}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  // Health and status endpoints
  async getHealth(): Promise<HealthStatus> {
    return this.request<HealthStatus>('/health');
  }

  async getAnkiStatus(): Promise<ApiResponse> {
    return this.request<ApiResponse>('/anki/status');
  }

  async getAnkiDecks(): Promise<ApiResponse> {
    return this.request<ApiResponse>('/anki/decks');
  }

  // Session management
  async createSession(config?: KotoriConfig): Promise<{session_id: string, message: string, timestamp: string}> {
    return this.request<{session_id: string, message: string, timestamp: string}>('/sessions', {
      method: 'POST',
      body: config ? JSON.stringify(config) : undefined,
    });
  }

  async getSession(sessionId: string): Promise<ApiResponse<{session: SessionState}>> {
    return this.request<ApiResponse<{session: SessionState}>>(`/sessions/${sessionId}`);
  }

  async listSessions(): Promise<ApiResponse<{active_sessions: string[], count: number}>> {
    return this.request<ApiResponse<{active_sessions: string[], count: number}>>('/sessions');
  }

  async updateSessionConfig(sessionId: string, config: KotoriConfig): Promise<ApiResponse> {
    return this.request<ApiResponse>(`/sessions/${sessionId}/config`, {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async updateUISettings(sessionId: string, uiSettings: UISettings): Promise<ApiResponse> {
    return this.request<ApiResponse>(`/sessions/${sessionId}/ui-settings`, {
      method: 'PUT',
      body: JSON.stringify(uiSettings),
    });
  }

  async closeSession(sessionId: string): Promise<ApiResponse> {
    return this.request<ApiResponse>(`/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  // Conversation history
  async getConversationHistory(sessionId: string, limit?: number): Promise<ConversationHistory> {
    const params = limit ? `?limit=${limit}` : '';
    return this.request<ConversationHistory>(`/sessions/${sessionId}/history${params}`);
  }

  async exportConversation(
    sessionId: string, 
    format: 'json' | 'txt' | 'csv' = 'json',
    includeMetadata: boolean = true
  ): Promise<ApiResponse<{data: string}>> {
    return this.request<ApiResponse<{data: string}>>(`/sessions/${sessionId}/history/export`, {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        format,
        include_metadata: includeMetadata,
      }),
    });
  }

  async clearConversationHistory(sessionId: string): Promise<ApiResponse> {
    return this.request<ApiResponse>(`/sessions/${sessionId}/history`, {
      method: 'DELETE',
    });
  }

  // Maintenance
  async cleanupSession(sessionId: string): Promise<ApiResponse> {
    return this.request<ApiResponse>(`/sessions/${sessionId}/cleanup`, {
      method: 'POST',
    });
  }

  async cleanupInactiveSessions(maxAgeHours: number = 24): Promise<ApiResponse<{cleaned_sessions: number}>> {
    return this.request<ApiResponse<{cleaned_sessions: number}>>('/maintenance/cleanup-inactive', {
      method: 'POST',
      body: JSON.stringify({ max_age_hours: maxAgeHours }),
    });
  }
}

export const apiService = new ApiService();

// Session creation lock to prevent concurrent requests
let sessionCreationInProgress = false;
let pendingSessionPromise: Promise<string> | null = null;

// Utility functions for common operations
export const apiUtils = {
  async createNewSession(config?: KotoriConfig): Promise<string> {
    // If a session creation is already in progress, return the same promise
    if (sessionCreationInProgress && pendingSessionPromise) {
      console.log('Session creation already in progress, waiting for existing request...');
      return pendingSessionPromise;
    }

    try {
      sessionCreationInProgress = true;
      console.log('Creating new session with config:', config);
      console.log('API_BASE_URL:', API_BASE_URL);
      
      pendingSessionPromise = (async () => {
        const response = await apiService.createSession(config);
        console.log('Session creation response:', response);
        // Backend returns session_id directly in response
        const sessionId = response.session_id || '';
        console.log('Session ID extracted:', sessionId);
        
        if (!sessionId || sessionId.trim() === '') {
          throw new Error('Invalid session ID received from server');
        }
        
        return sessionId;
      })();

      const result = await pendingSessionPromise;
      return result;
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    } finally {
      sessionCreationInProgress = false;
      pendingSessionPromise = null;
    }
  },

  async checkSystemHealth(): Promise<{isHealthy: boolean, issues: string[]}> {
    try {
      const health = await apiService.getHealth();
      const issues: string[] = [];
      
      if (health.services.anki !== 'connected') {
        issues.push('Anki connection issue');
      }
      
      if (health.services.azure_openai !== 'configured') {
        issues.push('Azure OpenAI configuration issue');
      }

      return {
        isHealthy: issues.length === 0,
        issues
      };
    } catch (error) {
      return {
        isHealthy: false,
        issues: ['API service unavailable']
      };
    }
  },

  async exportConversationToFile(
    sessionId: string, 
    format: 'json' | 'txt' | 'csv' = 'json'
  ): Promise<void> {
    try {
      const response = await apiService.exportConversation(sessionId, format);
      const data = response.data?.data || '';
      
      // Create and download file
      const blob = new Blob([data], { 
        type: format === 'json' ? 'application/json' : 'text/plain' 
      });
      
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `kotori-conversation-${sessionId}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export conversation:', error);
      throw error;
    }
  },

  formatApiError(error: any): string {
    if (error?.message) {
      return error.message;
    }
    if (typeof error === 'string') {
      return error;
    }
    return 'An unexpected error occurred';
  },

  isApiError(error: any): boolean {
    return error?.message && typeof error.message === 'string';
  }
};

// React Query keys for caching
export const queryKeys = {
  health: () => ['health'] as const,
  ankiStatus: () => ['anki', 'status'] as const,
  ankiDecks: () => ['anki', 'decks'] as const,
  session: (sessionId: string) => ['session', sessionId] as const,
  sessions: () => ['sessions'] as const,
  conversationHistory: (sessionId: string, limit?: number) => 
    ['conversation', sessionId, limit] as const,
};

// Custom hooks for API calls (to be used with React Query)
export const apiHooks = {
  useHealthQuery: () => queryKeys.health(),
  useAnkiStatusQuery: () => queryKeys.ankiStatus(),
  useAnkiDecksQuery: () => queryKeys.ankiDecks(),
  useSessionQuery: (sessionId: string) => queryKeys.session(sessionId),
  useSessionsQuery: () => queryKeys.sessions(),
  useConversationHistoryQuery: (sessionId: string, limit?: number) => 
    queryKeys.conversationHistory(sessionId, limit),
};