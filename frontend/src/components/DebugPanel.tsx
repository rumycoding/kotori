import React, { useState, useRef } from 'react';
import {
  Paper,
  Typography,
  Box,
  Divider,
  Chip,
  List,
  ListItem,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Close as CloseIcon,
  DragIndicator as DragIndicatorIcon
} from '@mui/icons-material';
import { format } from 'date-fns';
import { StateInfo, ToolCall, Message } from '../types';

interface DebugPanelProps {
  stateInfo?: StateInfo;
  toolCalls: ToolCall[];
  messages?: Message[];
  isVisible: boolean;
  onToggleVisibility: () => void;
}

const DebugPanel: React.FC<DebugPanelProps> = ({
  stateInfo,
  toolCalls,
  messages = [],
  isVisible,
  onToggleVisibility,
}) => {
  const [position, setPosition] = useState({ top: 500, right: 20 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const panelRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget || (e.target as HTMLElement).closest('.drag-handle')) {
      setIsDragging(true);
      const rect = panelRef.current?.getBoundingClientRect();
      if (rect) {
        setDragOffset({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      }
    }
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (isDragging) {
      const panelWidth = 350;
      const panelHeight = 400;
      const newLeft = e.clientX - dragOffset.x;
      const newTop = e.clientY - dragOffset.y;
      
      // Constrain to viewport boundaries
      const constrainedTop = Math.max(10, Math.min(window.innerHeight - panelHeight - 10, newTop));
      const constrainedLeft = Math.max(10, Math.min(window.innerWidth - panelWidth - 10, newLeft));
      const constrainedRight = window.innerWidth - constrainedLeft - panelWidth;
      
      setPosition({ top: constrainedTop, right: constrainedRight });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Extract tool calls from messages with message_type: 'tool'
  const extractToolCallsFromMessages = (): ToolCall[] => {
    const toolMessages = messages.filter(msg => msg.message_type === 'tool');
    return toolMessages.map(msg => {
      // Try to extract tool information from metadata or content
      let toolName = 'unknown_tool';
      let parameters = {};
      let status: 'pending' | 'success' | 'error' = 'success';
      
      if (msg.metadata) {
        toolName = msg.metadata.tool_name || msg.metadata.name || toolName;
        parameters = msg.metadata.parameters || msg.metadata.args || {};
        const metaStatus = msg.metadata.status;
        if (metaStatus === 'pending' || metaStatus === 'success' || metaStatus === 'error') {
          status = metaStatus;
        }
      }
      
      // If no metadata, try to parse from content
      if (toolName === 'unknown_tool' && msg.content) {
        try {
          // Look for tool call patterns in content
          const toolCallMatch = msg.content.match(/Tool:\s*(\w+)/i);
          if (toolCallMatch) {
            toolName = toolCallMatch[1];
          }
        } catch (e) {
          // Ignore parsing errors
        }
      }
      
      return {
        tool_name: toolName,
        parameters: parameters,
        status: status,
        result: msg.content,
        timestamp: msg.timestamp
      };
    });
  };

  // Combine explicit tool calls with tool messages - now using direct tool_calls from messages
  const toolMessagesFromState = extractToolCallsFromMessages();
  const directToolCalls = messages
    .filter(msg => msg.tool_calls && msg.tool_calls.length > 0)
    .flatMap(msg => msg.tool_calls || []);
  const allToolCalls = [...toolCalls, ...toolMessagesFromState, ...directToolCalls];

  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffset]);
  
  // Debug logging
  React.useEffect(() => {
    console.log('=== DEBUG PANEL STATE ===');
    console.log('Explicit toolCalls:', toolCalls);
    console.log('Messages:', messages);
    console.log('Tool messages found:', messages.filter(m => m.message_type === 'tool'));
    console.log('Messages with tool_calls:', messages.filter(m => m.tool_calls && m.tool_calls.length > 0));
    console.log('Extracted tool calls from messages:', toolMessagesFromState);
    console.log('Direct tool calls from messages:', directToolCalls);
    console.log('All tool calls combined:', allToolCalls);
    console.log('========================');
  }, [toolCalls, messages]);

  if (!isVisible) return null;

  const formatTimestamp = (timestamp: string) => {
    try {
      return format(new Date(timestamp), 'HH:mm:ss');
    } catch {
      return timestamp;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'success';
      case 'error': return 'error';
      case 'pending': return 'warning';
      default: return 'default';
    }
  };

  return (
    <Paper
      ref={panelRef}
      elevation={6}
      sx={{
        height: '600px',
        width: '400px',
        display: 'flex',
        flexDirection: 'column',
        position: 'fixed',
        top: `${position.top}px`,
        right: `${position.right}px`,
        zIndex: 1300,
        backgroundColor: 'background.paper',
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        cursor: isDragging ? 'grabbing' : 'default'
      }}
    >
      <Box
        className="drag-handle"
        onMouseDown={handleMouseDown}
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'grab',
          '&:active': {
            cursor: 'grabbing'
          }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <DragIndicatorIcon fontSize="small" color="action" />
          <Typography variant="h6">
            Debug Information
          </Typography>
        </Box>
        <IconButton
          size="small"
          onClick={onToggleVisibility}
          sx={{ ml: 1 }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>
      
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {/* Current State Information */}
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2" sx={{ color: 'primary.main' }}>
              Current State
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            {stateInfo ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Current Node:</Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {stateInfo.current_node}
                  </Typography>
                </Box>
                
                {stateInfo.next_node && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">Next Node:</Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                      {stateInfo.next_node}
                    </Typography>
                  </Box>
                )}
                
                {stateInfo.learning_goals && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">Learning Goals:</Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                      {stateInfo.learning_goals}
                    </Typography>
                  </Box>
                )}
                
                {stateInfo.active_cards && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">Active Cards:</Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                      {stateInfo.active_cards}
                    </Typography>
                  </Box>
                )}
                
                {stateInfo.assessment_history && (
                  <Box>
                    <Typography variant="caption" color="text.secondary">Assessment History:</Typography>
                    <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                      {stateInfo.assessment_history}
                    </Typography>
                  </Box>
                )}
                
                <Box>
                  <Typography variant="caption" color="text.secondary">Counter:</Typography>
                  <Typography variant="body2">{stateInfo.counter}</Typography>
                </Box>
                
                <Box>
                  <Typography variant="caption" color="text.secondary">Last Updated:</Typography>
                  <Typography variant="body2">{formatTimestamp(stateInfo.timestamp)}</Typography>
                </Box>
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No state information available
              </Typography>
            )}
          </AccordionDetails>
        </Accordion>

        {/* Tool Calls */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle2" sx={{ color: 'secondary.main' }}>
              Tool Calls ({allToolCalls.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 0 }}>
            {allToolCalls.length > 0 ? (
              <List sx={{ width: '100%', p: 0 }}>
                {allToolCalls.slice().reverse().slice(0, 10).map((tool, index) => (
                  <ListItem key={`${tool.timestamp}-${index}`} sx={{ px: 2, py: 1 }}>
                    <Box sx={{ width: '100%' }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                          {tool.tool_name}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                          <Chip
                            label={tool.status}
                            size="small"
                            color={getStatusColor(tool.status)}
                            sx={{ fontSize: '0.7rem' }}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {formatTimestamp(tool.timestamp)}
                          </Typography>
                        </Box>
                      </Box>
                      
                      {tool.parameters && Object.keys(tool.parameters).length > 0 && (
                        <Box sx={{ mt: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">Parameters:</Typography>
                          <Box sx={{
                            mt: 0.5,
                            p: 1,
                            bgcolor: 'grey.50',
                            borderRadius: 1,
                            border: '1px solid',
                            borderColor: 'grey.200'
                          }}>
                            {Object.entries(tool.parameters).map(([key, value], paramIndex) => (
                              <Box key={paramIndex} sx={{ mb: 0.5, '&:last-child': { mb: 0 } }}>
                                <Typography variant="caption" sx={{
                                  fontWeight: 'bold',
                                  color: 'primary.main',
                                  fontSize: '0.7rem'
                                }}>
                                  {key}:
                                </Typography>
                                <Typography variant="caption" sx={{
                                  display: 'block',
                                  fontFamily: 'monospace',
                                  fontSize: '0.7rem',
                                  ml: 1,
                                  wordBreak: 'break-all',
                                  whiteSpace: 'pre-wrap'
                                }}>
                                  {typeof value === 'object'
                                    ? JSON.stringify(value, null, 2)
                                    : String(value)
                                  }
                                </Typography>
                              </Box>
                            ))}
                          </Box>
                        </Box>
                      )}
                      
                      {tool.result && (
                        <Box sx={{ mt: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">Result:</Typography>
                          <Box sx={{
                            mt: 0.5,
                            p: 1,
                            bgcolor: 'grey.50',
                            borderRadius: 1,
                            border: '1px solid',
                            borderColor: 'grey.200',
                            maxHeight: '150px',
                            overflow: 'auto'
                          }}>
                            <Typography variant="caption" sx={{
                              display: 'block',
                              fontSize: '0.7rem',
                              fontFamily: 'monospace',
                              whiteSpace: 'pre-wrap',
                              wordBreak: 'break-word'
                            }}>
                              {typeof tool.result === 'object'
                                ? JSON.stringify(tool.result, null, 2)
                                : String(tool.result)
                              }
                            </Typography>
                          </Box>
                        </Box>
                      )}
                    </Box>
                  </ListItem>
                ))}
              </List>
            ) : (
              <Box sx={{ p: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  No tool calls recorded
                </Typography>
              </Box>
            )}
          </AccordionDetails>
        </Accordion>

      </Box>
    </Paper>
  );
};

export default DebugPanel;