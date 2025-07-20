import React from 'react';
import { Dialog, DialogTitle, DialogContent, Box, Typography, Switch, FormControlLabel } from '@mui/material';
import { VoiceSettings, UISettings } from '../types';

interface ControlPanelProps {
  voiceSettings: VoiceSettings;
  uiSettings: UISettings;
  onVoiceSettingsChange: (settings: VoiceSettings) => void;
  onUISettingsChange: (settings: UISettings) => void;
  open: boolean;
  onClose: () => void;
}

const ControlPanel: React.FC<ControlPanelProps> = ({
  voiceSettings,
  uiSettings,
  onVoiceSettingsChange,
  onUISettingsChange,
  open,
  onClose,
}) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Settings</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography variant="h6">Voice Settings</Typography>
          
          <FormControlLabel
            control={
              <Switch
                checked={voiceSettings.auto_play}
                onChange={(e) => onVoiceSettingsChange({
                  ...voiceSettings,
                  auto_play: e.target.checked
                })}
              />
            }
            label="Auto-play AI responses"
          />

          <Typography variant="h6">UI Settings</Typography>
          
          <FormControlLabel
            control={
              <Switch
                checked={uiSettings.theme === 'dark'}
                onChange={(e) => onUISettingsChange({
                  ...uiSettings,
                  theme: e.target.checked ? 'dark' : 'light'
                })}
              />
            }
            label="Dark mode"
          />
          
          <FormControlLabel
            control={
              <Switch
                checked={uiSettings.debug_mode}
                onChange={(e) => onUISettingsChange({
                  ...uiSettings,
                  debug_mode: e.target.checked
                })}
              />
            }
            label="Debug mode"
          />
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default ControlPanel;