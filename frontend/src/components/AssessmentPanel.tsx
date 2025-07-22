import React, { useState, useRef } from 'react';
import {
  Paper,
  Typography,
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CloseIcon from '@mui/icons-material/Close';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';

interface AssessmentPanelProps {
  assessmentHistory?: string[];
  isVisible: boolean;
  onToggleVisibility: () => void;
}

const AssessmentPanel: React.FC<AssessmentPanelProps> = ({
  assessmentHistory,
  isVisible,
  onToggleVisibility,
}) => {
  const [position, setPosition] = useState({ top: 80, right: 20 });
  const [size, setSize] = useState({ width: 350, height: 400 });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<string>('');
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, width: 0, height: 0 });
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
      const newLeft = e.clientX - dragOffset.x;
      const newTop = e.clientY - dragOffset.y;
      
      // Constrain to viewport boundaries
      const constrainedTop = Math.max(10, Math.min(window.innerHeight - size.height - 10, newTop));
      const constrainedLeft = Math.max(10, Math.min(window.innerWidth - size.width - 10, newLeft));
      const constrainedRight = window.innerWidth - constrainedLeft - size.width;
      
      setPosition({ top: constrainedTop, right: constrainedRight });
    } else if (isResizing) {
      const deltaX = e.clientX - resizeStart.x;
      const deltaY = e.clientY - resizeStart.y;
      
      let newWidth = resizeStart.width;
      let newHeight = resizeStart.height;
      
      // Handle different resize directions
      if (resizeHandle.includes('right')) {
        newWidth = Math.max(250, Math.min(600, resizeStart.width + deltaX));
      }
      if (resizeHandle.includes('left')) {
        newWidth = Math.max(250, Math.min(600, resizeStart.width - deltaX));
      }
      if (resizeHandle.includes('bottom')) {
        newHeight = Math.max(200, Math.min(800, resizeStart.height + deltaY));
      }
      if (resizeHandle.includes('top')) {
        newHeight = Math.max(200, Math.min(800, resizeStart.height - deltaY));
      }
      
      setSize({ width: newWidth, height: newHeight });
      
      // Adjust position if resizing from left or top
      if (resizeHandle.includes('left')) {
        const widthDiff = newWidth - size.width;
        setPosition(prev => ({ ...prev, right: prev.right + widthDiff }));
      }
      if (resizeHandle.includes('top')) {
        const heightDiff = newHeight - size.height;
        setPosition(prev => ({ ...prev, top: prev.top - heightDiff }));
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setIsResizing(false);
    setResizeHandle('');
  };

  const handleResizeStart = (e: React.MouseEvent, handle: string) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
    setResizeHandle(handle);
    setResizeStart({
      x: e.clientX,
      y: e.clientY,
      width: size.width,
      height: size.height
    });
  };

  React.useEffect(() => {
    if (isDragging || isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, dragOffset, resizeStart, size]);

  if (!isVisible) return null;

  // Function to render markdown-like text with basic formatting
  const renderMarkdown = (text: string) => {
    // Split by lines and process each
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    
    lines.forEach((line, lineIndex) => {
      // Handle headers
      if (line.startsWith('# ')) {
        elements.push(
          <Typography key={lineIndex} variant="h6" sx={{ mt: 2, mb: 1, fontWeight: 'bold' }}>
            {line.slice(2)}
          </Typography>
        );
      } else if (line.startsWith('## ')) {
        elements.push(
          <Typography key={lineIndex} variant="subtitle1" sx={{ mt: 1.5, mb: 0.5, fontWeight: 'bold' }}>
            {line.slice(3)}
          </Typography>
        );
      } else if (line.startsWith('### ')) {
        elements.push(
          <Typography key={lineIndex} variant="subtitle2" sx={{ mt: 1, mb: 0.5, fontWeight: 'bold' }}>
            {line.slice(4)}
          </Typography>
        );
      }
      // Handle bullet points
      else if (line.startsWith('- ') || line.startsWith('* ')) {
        elements.push(
          <Typography key={lineIndex} variant="body2" sx={{ ml: 2, mb: 0.5 }}>
            • {line.slice(2)}
          </Typography>
        );
      }
      // Handle numbered lists
      else if (/^\d+\.\s/.test(line)) {
        elements.push(
          <Typography key={lineIndex} variant="body2" sx={{ ml: 2, mb: 0.5 }}>
            {line}
          </Typography>
        );
      }
      // Handle bold text **text**
      else if (line.includes('**')) {
        const parts = line.split('**');
        const formattedParts = parts.map((part, index) =>
          index % 2 === 1 ? <strong key={index}>{part}</strong> : part
        );
        elements.push(
          <Typography key={lineIndex} variant="body2" sx={{ mb: 0.5 }}>
            {formattedParts}
          </Typography>
        );
      }
      // Handle empty lines
      else if (line.trim() === '') {
        elements.push(<Box key={lineIndex} sx={{ height: '8px' }} />);
      }
      // Regular text
      else if (line.trim() !== '') {
        elements.push(
          <Typography key={lineIndex} variant="body2" sx={{ mb: 0.5 }}>
            {line}
          </Typography>
        );
      }
    });
    
    return elements;
  };

  const formatTimestamp = (originalIndex: number) => {
    const now = new Date();
    const assessmentTime = new Date(now.getTime() - (assessmentHistory!.length - 1 - originalIndex) * 60000);
    return assessmentTime.toLocaleTimeString();
  };

  return (
    <Paper
      ref={panelRef}
      elevation={6}
      sx={{
        height: `${size.height}px`,
        width: `${size.width}px`,
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
      {/* Resize handles */}
      {/* Right edge */}
      <Box
        onMouseDown={(e) => handleResizeStart(e, 'right')}
        sx={{
          position: 'absolute',
          right: 0,
          top: 8,
          bottom: 8,
          width: '4px',
          cursor: 'ew-resize',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: 'primary.main',
            opacity: 0.3
          }
        }}
      />
      
      {/* Bottom edge */}
      <Box
        onMouseDown={(e) => handleResizeStart(e, 'bottom')}
        sx={{
          position: 'absolute',
          bottom: 0,
          left: 8,
          right: 8,
          height: '4px',
          cursor: 'ns-resize',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: 'primary.main',
            opacity: 0.3
          }
        }}
      />
      
      {/* Bottom-right corner */}
      <Box
        onMouseDown={(e) => handleResizeStart(e, 'bottom-right')}
        sx={{
          position: 'absolute',
          bottom: 0,
          right: 0,
          width: '8px',
          height: '8px',
          cursor: 'nw-resize',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: 'primary.main',
            opacity: 0.5
          }
        }}
      />
      
      {/* Left edge */}
      <Box
        onMouseDown={(e) => handleResizeStart(e, 'left')}
        sx={{
          position: 'absolute',
          left: 0,
          top: 8,
          bottom: 8,
          width: '4px',
          cursor: 'ew-resize',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: 'primary.main',
            opacity: 0.3
          }
        }}
      />
      
      {/* Top edge */}
      <Box
        onMouseDown={(e) => handleResizeStart(e, 'top')}
        sx={{
          position: 'absolute',
          top: 0,
          left: 8,
          right: 8,
          height: '4px',
          cursor: 'ns-resize',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: 'primary.main',
            opacity: 0.3
          }
        }}
      />
      
      {/* Top-left corner */}
      <Box
        onMouseDown={(e) => handleResizeStart(e, 'top-left')}
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '8px',
          height: '8px',
          cursor: 'nw-resize',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: 'primary.main',
            opacity: 0.5
          }
        }}
      />
      
      {/* Top-right corner */}
      <Box
        onMouseDown={(e) => handleResizeStart(e, 'top-right')}
        sx={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: '8px',
          height: '8px',
          cursor: 'ne-resize',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: 'primary.main',
            opacity: 0.5
          }
        }}
      />
      
      {/* Bottom-left corner */}
      <Box
        onMouseDown={(e) => handleResizeStart(e, 'bottom-left')}
        sx={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          width: '8px',
          height: '8px',
          cursor: 'ne-resize',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: 'primary.main',
            opacity: 0.5
          }
        }}
      />
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
            Assessment History
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
      
      <Box sx={{ flex: 1, overflow: 'auto', p: 1 }}>
        {assessmentHistory && assessmentHistory.length > 0 ? (
          <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            {[...assessmentHistory].reverse().map((assessment, index) => {
              const originalIndex = assessmentHistory.length - 1 - index;
              const isLatest = index === 0; // First item in reversed array is the latest
              
              return (
                <Accordion
                  key={originalIndex}
                  defaultExpanded={isLatest}
                  sx={{
                    mb: 1,
                    '&:before': { display: 'none' },
                    boxShadow: 1,
                    borderRadius: 1,
                    '&.Mui-expanded': {
                      margin: '0 0 8px 0',
                    }
                  }}
                >
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    sx={{
                      bgcolor: isLatest ? 'primary.light' : 'grey.100',
                      color: isLatest ? 'primary.contrastText' : 'text.primary',
                      '&.Mui-expanded': {
                        minHeight: 48,
                      },
                      '& .MuiAccordionSummary-content': {
                        margin: '12px 0',
                        '&.Mui-expanded': {
                          margin: '12px 0',
                        }
                      }
                    }}
                  >
                    <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                        {isLatest ? '🔥 Latest Assessment' : `Assessment #${originalIndex + 1}`}
                      </Typography>
                      <Typography variant="caption" sx={{ opacity: 0.8 }}>
                        {formatTimestamp(originalIndex)}
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails sx={{ pt: 1, pb: 2 }}>
                    <Box sx={{
                      '& > *:first-of-type': { mt: 0 },
                      '& > *:last-child': { mb: 0 }
                    }}>
                      {renderMarkdown(assessment)}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              );
            })}
          </Box>
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