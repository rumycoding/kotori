import React, { useState, useRef } from 'react';
import {
  Box,
  TextField,
  IconButton,
  Paper,
  Tooltip,
  Typography,
  Chip,
} from '@mui/material';
import {
  Send as SendIcon,
  Mic as MicIcon,
  MicOff as MicOffIcon,
  VolumeUp as SpeakerIcon,
} from '@mui/icons-material';

import { VoiceSettings } from '../types';

interface InputComponentProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  voiceEnabled?: boolean;
  voiceSettings?: VoiceSettings;
}

const InputComponent: React.FC<InputComponentProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = 'Type your message...',
  voiceEnabled = false,
  voiceSettings,
}) => {
  const [message, setMessage] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const recognitionRef = useRef<any>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const startListening = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Speech recognition is not supported in this browser');
      return;
    }

    try {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US'; // This could be dynamic based on settings

      recognitionRef.current.onstart = () => {
        setIsListening(true);
        setTranscript('');
      };

      recognitionRef.current.onresult = (event: any) => {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) {
            finalTranscript += result[0].transcript;
          } else {
            interimTranscript += result[0].transcript;
          }
        }

        setTranscript(interimTranscript);
        
        if (finalTranscript) {
          setMessage(prev => prev + finalTranscript);
          setTranscript('');
        }
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
        setTranscript('');
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        setTranscript('');
      };

      recognitionRef.current.start();
    } catch (error) {
      console.error('Failed to start speech recognition:', error);
      alert('Failed to start speech recognition');
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsListening(false);
    setTranscript('');
  };

  const testTTS = () => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance('This is a test of the text-to-speech feature.');
      
      if (voiceSettings) {
        utterance.rate = voiceSettings.rate;
        utterance.pitch = voiceSettings.pitch;
        utterance.volume = voiceSettings.volume;
      }

      speechSynthesis.speak(utterance);
    } else {
      alert('Text-to-speech is not supported in this browser');
    }
  };

  return (
    <Paper elevation={1} sx={{ p: 2 }}>
      <Box component="form" onSubmit={handleSubmit}>
        {/* Voice Recognition Status */}
        {isListening && (
          <Box sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              label="Listening..."
              color="primary"
              size="small"
              icon={<MicIcon />}
            />
            {transcript && (
              <Typography variant="caption" color="text.secondary">
                "{transcript}"
              </Typography>
            )}
          </Box>
        )}

        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          {/* Text Input */}
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            disabled={disabled}
            variant="outlined"
            size="small"
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              },
            }}
          />

          {/* Voice Input Button */}
          {voiceEnabled && (
            <Tooltip title={isListening ? 'Stop listening' : 'Start voice input'}>
              <span>
                <IconButton
                  onClick={isListening ? stopListening : startListening}
                  disabled={disabled}
                  color={isListening ? 'secondary' : 'default'}
                  sx={{
                    bgcolor: isListening ? 'secondary.light' : 'transparent',
                  }}
                >
                  {isListening ? <MicOffIcon /> : <MicIcon />}
                </IconButton>
              </span>
            </Tooltip>
          )}

          {/* TTS Test Button */}
          {voiceSettings && (
            <Tooltip title="Test text-to-speech">
              <span>
                <IconButton
                  onClick={testTTS}
                  disabled={disabled}
                  color="default"
                >
                  <SpeakerIcon />
                </IconButton>
              </span>
            </Tooltip>
          )}

          {/* Send Button */}
          <Tooltip title="Send message">
            <span>
              <IconButton
                type="submit"
                disabled={disabled || !message.trim()}
                color="primary"
                sx={{
                  bgcolor: !disabled && message.trim() ? 'primary.main' : 'transparent',
                  color: !disabled && message.trim() ? 'primary.contrastText' : 'text.secondary',
                  '&:hover': {
                    bgcolor: !disabled && message.trim() ? 'primary.dark' : 'transparent',
                  },
                }}
              >
                <SendIcon />
              </IconButton>
            </span>
          </Tooltip>
        </Box>

        {/* Help Text */}
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Press Enter to send, Shift+Enter for new line
          {voiceEnabled && ' • Click mic for voice input'}
        </Typography>
      </Box>
    </Paper>
  );
};

export default InputComponent;