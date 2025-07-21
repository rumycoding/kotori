import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Avatar,
  Chip,
  CircularProgress,
  List,
  ListItem,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Person as PersonIcon,
  SmartToy as BotIcon,
  Build as ToolIcon,
  Info as InfoIcon,
  VolumeUp as VolumeUpIcon,
  VolumeOff as VolumeOffIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { format } from 'date-fns';

import { Message } from '../types';

interface MessageDisplayProps {
  messages: Message[];
  isLoading?: boolean;
  onMessageClick?: (message: Message) => void;
  onSpeakText?: (text: string, messageId: string) => void;
  onStopSpeech?: () => void;
  isSpeaking?: boolean;
  speakingMessageId?: string;
}

const MessageDisplay: React.FC<MessageDisplayProps> = ({
  messages,
  isLoading = false,
  onMessageClick,
  onSpeakText,
  onStopSpeech,
  isSpeaking = false,
  speakingMessageId
}) => {
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const getMessageIcon = (messageType: Message['message_type']) => {
    switch (messageType) {
      case 'user':
        return <PersonIcon />;
      case 'ai':
        return <BotIcon />;
      case 'tool':
        return <ToolIcon />;
      case 'system':
        return <InfoIcon />;
      default:
        return <InfoIcon />;
    }
  };

  const getMessageColor = (messageType: Message['message_type']) => {
    switch (messageType) {
      case 'user':
        return 'primary.main';
      case 'ai':
        return 'secondary.main';
      case 'tool':
        return 'info.main';
      case 'system':
        return 'warning.main';
      default:
        return 'grey.500';
    }
  };

  const getMessageAlignment = (messageType: Message['message_type']) => {
    return messageType === 'user' ? 'flex-end' : 'flex-start';
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      return format(new Date(timestamp), 'HH:mm:ss');
    } catch {
      return '';
    }
  };

  return (
    <Box
      sx={{
        height: '100%',
        overflow: 'auto',
        overflowX: 'hidden',
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        '&::-webkit-scrollbar': {
          width: '8px',
        },
        '&::-webkit-scrollbar-track': {
          background: '#f1f1f1',
          borderRadius: '4px',
        },
        '&::-webkit-scrollbar-thumb': {
          background: '#888',
          borderRadius: '4px',
          '&:hover': {
            background: '#555',
          },
        },
        scrollBehavior: 'smooth',
      }}
    >
      {messages.length === 0 ? (
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: 2,
            color: 'text.secondary',
          }}
        >
          <BotIcon sx={{ fontSize: 64, opacity: 0.3 }} />
          <Typography variant="h6" align="center">
            Welcome to Kotori!
          </Typography>
          <Typography variant="body2" align="center" sx={{ maxWidth: 400 }}>
            Start a conversation to practice your language skills. I'm here to help you learn!
          </Typography>
        </Box>
      ) : (
        <List sx={{ width: '100%', p: 0 }}>
          {messages.map((message) => (
            <ListItem
              key={message.id}
              sx={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: getMessageAlignment(message.message_type),
                mb: 2,
                px: 0,
                cursor: onMessageClick ? 'pointer' : 'default',
              }}
              onClick={() => onMessageClick?.(message)}
            >
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: message.message_type === 'user' ? 'row-reverse' : 'row',
                  alignItems: 'flex-start',
                  gap: 1,
                  maxWidth: '80%',
                }}
              >
                {/* Avatar */}
                <Avatar
                  sx={{
                    bgcolor: getMessageColor(message.message_type),
                    width: 32,
                    height: 32,
                  }}
                >
                  {getMessageIcon(message.message_type)}
                </Avatar>

                {/* Message Content */}
                <Paper
                  elevation={1}
                  sx={{
                    p: 2,
                    bgcolor: message.message_type === 'user' ? 'primary.light' : 'background.paper',
                    color: message.message_type === 'user' ? 'primary.contrastText' : 'text.primary',
                    borderRadius: 2,
                    maxWidth: '100%',
                    wordBreak: 'break-word',
                  }}
                >
                  {/* Message Type Chip */}
                  {message.message_type !== 'user' && message.message_type !== 'ai' && (
                    <Chip
                      label={message.message_type.toUpperCase()}
                      size="small"
                      sx={{ mb: 1 }}
                      color="default"
                    />
                  )}

                  {/* Message Text */}
                  <Box sx={{ mb: 1 }}>
                    {message.message_type === 'ai' ? (
                      <ReactMarkdown
                        components={{
                          p: ({ children }) => (
                            <Typography variant="body1" component="div" sx={{ mb: 1 }}>
                              {children}
                            </Typography>
                          ),
                          code: ({ children, className }) => {
                            const isInline = !className;
                            return (
                              <Box
                                component={isInline ? 'code' : 'pre'}
                                sx={{
                                  fontFamily: 'monospace',
                                  fontSize: '0.875rem',
                                  bgcolor: 'grey.100',
                                  p: isInline ? 0.5 : 1,
                                  borderRadius: 1,
                                  display: isInline ? 'inline' : 'block',
                                  whiteSpace: isInline ? 'normal' : 'pre-wrap',
                                  overflow: 'auto',
                                }}
                              >
                                {children}
                              </Box>
                            );
                          },
                          ul: ({ children, ...props }) => (
                            <Box component="ul" sx={{ pl: 2, mb: 1 }}>
                              {React.Children.map(children, (child, index) =>
                                React.isValidElement(child)
                                  ? React.cloneElement(child, {
                                      key: `${message.id}-ul-item-${index}`,
                                      ...child.props
                                    })
                                  : child
                              )}
                            </Box>
                          ),
                          ol: ({ children, ...props }) => (
                            <Box component="ol" sx={{ pl: 2, mb: 1 }}>
                              {React.Children.map(children, (child, index) =>
                                React.isValidElement(child)
                                  ? React.cloneElement(child, {
                                      key: `${message.id}-ol-item-${index}`,
                                      ...child.props
                                    })
                                  : child
                              )}
                            </Box>
                          ),
                          li: ({ children, node, ordered, ...props }) => {
                            // Use node position or content hash for stable key
                            const nodeKey = node?.position?.start?.line ||
                                          (typeof children === 'string' ? children.slice(0, 20) : 'item');
                            // Filter out 'ordered' prop as it's not a valid HTML li attribute
                            return (
                              <li key={`${message.id}-li-${nodeKey}`} {...props}>
                                {children}
                              </li>
                            );
                          },
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    ) : (
                      <Typography variant="body1">
                        {message.content}
                      </Typography>
                    )}
                  </Box>

                  {/* Timestamp and Voice Controls */}
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: message.message_type === 'user' ? 'flex-end' : 'space-between',
                      alignItems: 'center',
                      mt: 0.5,
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        opacity: 0.7,
                      }}
                    >
                      {formatTimestamp(message.timestamp)}
                    </Typography>
                    
                    {/* Voice Icon for AI messages */}
                    {message.message_type === 'ai' && onSpeakText && (
                      <Tooltip title={isSpeaking && speakingMessageId === message.id ? "Stop speech" : "Listen to this message"}>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (isSpeaking && speakingMessageId === message.id) {
                              onStopSpeech?.();
                            } else {
                              onSpeakText(message.content, message.id);
                            }
                          }}
                          sx={{
                            ml: 1,
                            opacity: isSpeaking && speakingMessageId === message.id ? 1 : 0.7,
                            color: isSpeaking && speakingMessageId === message.id ? 'primary.main' : 'inherit',
                            '&:hover': {
                              opacity: 1,
                              bgcolor: 'action.hover'
                            }
                          }}
                        >
                          {isSpeaking && speakingMessageId === message.id ? (
                            <VolumeOffIcon fontSize="small" />
                          ) : (
                            <VolumeUpIcon fontSize="small" />
                          )}
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>

                  {/* Metadata */}
                  {message.metadata && Object.keys(message.metadata).length > 0 && (
                    <Box sx={{ mt: 1, opacity: 0.8 }}>
                      {Object.entries(message.metadata).map(([key, value]) => (
                        <Chip
                          key={key}
                          label={`${key}: ${value}`}
                          size="small"
                          variant="outlined"
                          sx={{ mr: 0.5, mb: 0.5 }}
                        />
                      ))}
                    </Box>
                  )}
                </Paper>
              </Box>
            </ListItem>
          ))}
        </List>
      )}

      {/* Loading Indicator */}
      {isLoading && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-start',
            gap: 1,
            px: 2,
          }}
        >
          <Avatar sx={{ bgcolor: 'secondary.main', width: 32, height: 32 }}>
            <BotIcon />
          </Avatar>
          <Paper
            elevation={1}
            sx={{
              p: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              borderRadius: 2,
            }}
          >
            <CircularProgress size={16} />
            <Typography variant="body2" color="text.secondary">
              Kotori is thinking...
            </Typography>
          </Paper>
        </Box>
      )}

      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </Box>
  );
};

export default MessageDisplay;