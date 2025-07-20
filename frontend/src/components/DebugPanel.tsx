import React from 'react';
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
  AccordionDetails
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon } from '@mui/icons-material';
import { format } from 'date-fns';
import { StateInfo, ToolCall } from '../types';

interface DebugPanelProps {
  stateInfo?: StateInfo;
  toolCalls: ToolCall[];
  isVisible: boolean;
  onToggleVisibility: () => void;
}

const DebugPanel: React.FC<DebugPanelProps> = ({
  stateInfo,
  toolCalls,
  isVisible,
  onToggleVisibility,
}) => {
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
    <Paper elevation={2} sx={{ height: '400px', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6">
          Debug Information
        </Typography>
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
              Tool Calls ({toolCalls.length})
            </Typography>
          </AccordionSummary>
          <AccordionDetails sx={{ p: 0 }}>
            {toolCalls.length > 0 ? (
              <List sx={{ width: '100%', p: 0 }}>
                {toolCalls.slice().reverse().slice(0, 10).map((tool, index) => (
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
                          <Typography variant="caption" sx={{
                            display: 'block',
                            fontFamily: 'monospace',
                            fontSize: '0.7rem',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}>
                            {JSON.stringify(tool.parameters)}
                          </Typography>
                        </Box>
                      )}
                      
                      {tool.result && (
                        <Box sx={{ mt: 0.5 }}>
                          <Typography variant="caption" color="text.secondary">Result:</Typography>
                          <Typography variant="caption" sx={{
                            display: 'block',
                            fontSize: '0.7rem',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}>
                            {tool.result}
                          </Typography>
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