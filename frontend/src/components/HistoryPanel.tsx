import React from 'react';
import { Dialog, DialogTitle, DialogContent, Box, Button } from '@mui/material';
import { Message } from '../types';

interface HistoryPanelProps {
  messages: Message[];
  onExport: (format: 'json' | 'txt' | 'csv') => void;
  onClear: () => void;
  onSearch: (query: string) => Message[];
  isVisible: boolean;
  onToggleVisibility: () => void;
}

const HistoryPanel: React.FC<HistoryPanelProps> = ({
  messages,
  onExport,
  onClear,
  onSearch,
  isVisible,
  onToggleVisibility,
}) => {
  return (
    <Dialog open={isVisible} onClose={onToggleVisibility} maxWidth="md" fullWidth>
      <DialogTitle>Conversation History</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Button onClick={() => onExport('json')}>Export JSON</Button>
          <Button onClick={() => onExport('txt')}>Export TXT</Button>
          <Button onClick={onClear} color="error">Clear History</Button>
        </Box>
        <Box>
          {messages.length} messages in history
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default HistoryPanel;