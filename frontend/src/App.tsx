import React, { useState, useEffect, useRef } from 'react';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Box,
  CircularProgress,
  Typography,
  Alert,
  Container,
} from '@mui/material';

import { KotoriConfig, UISettings, VoiceSettings } from './types';
import { apiUtils } from './services/api';
import ChatInterface from './components/ChatInterface';

// Create theme
const createAppTheme = (mode: 'light' | 'dark') => createTheme({
  palette: {
    mode,
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});

const App: React.FC = () => {
  // Application state
  const [sessionId, setSessionId] = useState<string>('');
  const [config, setConfig] = useState<KotoriConfig>({
    language: 'english',
    deck_name: 'Kotori',
  });
  const [uiSettings, setUISettings] = useState<UISettings>({
    theme: 'light',
    debug_mode: false,
    show_assessment: true,
    show_debug_panel: false,
    voice_settings: {
      rate: 1.0,
      pitch: 1.0,
      volume: 1.0,
      auto_play: true,
    },
  });

  // Loading and error states
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [systemHealth, setSystemHealth] = useState<{isHealthy: boolean, issues: string[]}>({
    isHealthy: true,
    issues: [],
  });

  // Session initialization state to prevent duplicate creation
  const [isInitializing, setIsInitializing] = useState(false);
  const initializationRef = useRef(false);
  const sessionIdRef = useRef<string>('');

  // Initialize app
  useEffect(() => {
    // Use ref-based approach that survives React StrictMode's double-invocation
    if (initializationRef.current) {
      console.log('App initialization already completed via ref, skipping');
      return;
    }

    // Check if we already have a valid session from sessionStorage
    const existingSessionId = sessionStorage.getItem('kotori_session_id');
    if (existingSessionId && existingSessionId.trim() !== '' && sessionIdRef.current === '') {
      console.log('Found existing session ID in sessionStorage:', existingSessionId);
      sessionIdRef.current = existingSessionId;
      setSessionId(existingSessionId);
      loadSavedSettings();
      setIsLoading(false);
      initializationRef.current = true;
      return;
    }

    // Mark as initializing to prevent duplicate calls
    initializationRef.current = true;
    console.log('Starting app initialization...');
    
    initializeApp();
    
    // Setup cleanup for page unload
    const handleBeforeUnload = () => {
      sessionStorage.removeItem('kotori_session_id');
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    // Cleanup function
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  const initializeApp = async () => {
    try {
      setIsLoading(true);
      setError('');

      // Check if we already have a valid session from previous initialization
      const existingSessionId = sessionStorage.getItem('kotori_session_id');
      if (existingSessionId && existingSessionId.trim() !== '' && sessionIdRef.current === '') {
        console.log('Found existing session ID:', existingSessionId);
        sessionIdRef.current = existingSessionId;
        setSessionId(existingSessionId);
        
        // Load saved settings from localStorage
        loadSavedSettings();
        
        // Check system health
        const health = await apiUtils.checkSystemHealth();
        setSystemHealth(health);
        
        console.log('App reinitialized with existing session');
        return;
      }

      // Skip if we already have a session ID
      if (sessionIdRef.current !== '') {
        console.log('Session already exists, skipping initialization');
        setSessionId(sessionIdRef.current);
        setIsLoading(false);
        return;
      }

      // Check system health
      const health = await apiUtils.checkSystemHealth();
      setSystemHealth(health);

      // Create new session only if we don't have one
      console.log('Creating new session...');
      const newSessionId = await apiUtils.createNewSession(config);
      
      if (!newSessionId || newSessionId.trim() === '') {
        throw new Error('Failed to create session - invalid session ID received');
      }
      
      console.log('New session created:', newSessionId);
      sessionIdRef.current = newSessionId;
      setSessionId(newSessionId);
      
      // Store session ID to prevent recreation on re-renders
      sessionStorage.setItem('kotori_session_id', newSessionId);

      // Load saved settings from localStorage
      loadSavedSettings();

      console.log('App initialization completed successfully');

    } catch (err) {
      console.error('Failed to initialize app:', err);
      setError('Failed to initialize the application. Please refresh and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadSavedSettings = () => {
    try {
      // Load config from localStorage
      const savedConfig = localStorage.getItem('kotori_config');
      if (savedConfig) {
        const parsedConfig = JSON.parse(savedConfig);
        setConfig({ ...config, ...parsedConfig });
      }

      // Load UI settings from localStorage
      const savedUISettings = localStorage.getItem('kotori_ui_settings');
      if (savedUISettings) {
        const parsedSettings = JSON.parse(savedUISettings);
        setUISettings({ ...uiSettings, ...parsedSettings });
      }
    } catch (err) {
      console.warn('Failed to load saved settings:', err);
    }
  };

  const handleConfigChange = (newConfig: KotoriConfig) => {
    setConfig(newConfig);
    
    // Save to localStorage
    try {
      localStorage.setItem('kotori_config', JSON.stringify(newConfig));
    } catch (err) {
      console.warn('Failed to save config to localStorage:', err);
    }
  };

  const handleUISettingsChange = (newSettings: UISettings) => {
    setUISettings(newSettings);
    
    // Save to localStorage
    try {
      localStorage.setItem('kotori_ui_settings', JSON.stringify(newSettings));
    } catch (err) {
      console.warn('Failed to save UI settings to localStorage:', err);
    }
  };

  const handleRetry = () => {
    // Clear existing session to force creation of new one
    sessionStorage.removeItem('kotori_session_id');
    setSessionId('');
    
    // Reset refs to allow re-initialization
    initializationRef.current = false;
    sessionIdRef.current = '';
    
    initializeApp();
  };

  // Create theme based on settings
  const theme = createAppTheme(uiSettings.theme);

  // Loading screen
  if (isLoading) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box
          sx={{
            height: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          <CircularProgress size={60} />
          <Typography variant="h6" color="text.secondary">
            Initializing Kotori...
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Setting up your language learning session
          </Typography>
        </Box>
      </ThemeProvider>
    );
  }

  // Error screen
  if (error) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Container maxWidth="sm">
          <Box
            sx={{
              height: '100vh',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexDirection: 'column',
              gap: 3,
            }}
          >
            <Typography variant="h4" color="error" align="center">
              Oops! Something went wrong
            </Typography>
            
            <Alert severity="error" sx={{ width: '100%' }}>
              {error}
            </Alert>

            {!systemHealth.isHealthy && (
              <Alert severity="warning" sx={{ width: '100%' }}>
                <Typography variant="subtitle2" gutterBottom>
                  System Issues Detected:
                </Typography>
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {systemHealth.issues.map((issue, index) => (
                    <li key={index}>{issue}</li>
                  ))}
                </ul>
              </Alert>
            )}

            <Box sx={{ display: 'flex', gap: 2 }}>
              <button
                onClick={handleRetry}
                style={{
                  padding: '8px 16px',
                  backgroundColor: theme.palette.primary.main,
                  color: theme.palette.primary.contrastText,
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                Retry
              </button>
              <button
                onClick={() => window.location.reload()}
                style={{
                  padding: '8px 16px',
                  backgroundColor: theme.palette.secondary.main,
                  color: theme.palette.secondary.contrastText,
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                Refresh Page
              </button>
            </Box>
          </Box>
        </Container>
      </ThemeProvider>
    );
  }

  // Main app
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      
      {/* System Health Warning */}
      {!systemHealth.isHealthy && (
        <Alert 
          severity="warning" 
          sx={{ 
            borderRadius: 0,
            '& .MuiAlert-message': {
              width: '100%'
            }
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <Box>
              <Typography variant="body2" component="span">
                System issues detected: {systemHealth.issues.join(', ')}
              </Typography>
            </Box>
            <button
              onClick={() => setSystemHealth({isHealthy: true, issues: []})}
              style={{
                background: 'none',
                border: 'none',
                color: 'inherit',
                cursor: 'pointer',
                padding: '4px',
              }}
            >
              ✕
            </button>
          </Box>
        </Alert>
      )}

      {/* Main Chat Interface */}
      <ChatInterface
        sessionId={sessionId}
        config={config}
        uiSettings={uiSettings}
        onConfigChange={handleConfigChange}
        onUISettingsChange={handleUISettingsChange}
      />
    </ThemeProvider>
  );
};

export default App;