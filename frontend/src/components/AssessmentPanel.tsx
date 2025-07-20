import React from 'react';
import {
  Paper,
  Typography,
  Box
} from '@mui/material';

interface AssessmentPanelProps {
  assessmentHistory?: string;
  isVisible: boolean;
  onToggleVisibility: () => void;
}

const AssessmentPanel: React.FC<AssessmentPanelProps> = ({
  assessmentHistory,
  isVisible,
  onToggleVisibility,
}) => {
  if (!isVisible) return null;

  return (
    <Paper elevation={2} sx={{ height: '400px', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6">
          Assessment History
        </Typography>
      </Box>
      
      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {assessmentHistory ? (
          <Typography
            variant="body2"
            sx={{
              whiteSpace: 'pre-wrap',
              fontSize: '0.875rem',
              lineHeight: 1.5
            }}
          >
            {assessmentHistory}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No assessment history available
          </Typography>
        )}
      </Box>
    </Paper>
  );
};

export default AssessmentPanel;