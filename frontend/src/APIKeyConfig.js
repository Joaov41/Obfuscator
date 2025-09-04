import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  Alert,
  IconButton,
  InputAdornment,
  Chip,
  Grid
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Settings as SettingsIcon,
  Check as CheckIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

export default function APIKeyConfig({ open, onClose, onConfigured }) {
  const [openaiKey, setOpenaiKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [showOpenaiKey, setShowOpenaiKey] = useState(false);
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [keyStatus, setKeyStatus] = useState({ openai_configured: false, gemini_configured: false });

  useEffect(() => {
    checkKeyStatus();
  }, []);

  const checkKeyStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/check-keys`);
      setKeyStatus(response.data);
    } catch (err) {
      console.error('Failed to check key status:', err);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await axios.post(`${API_BASE}/api/configure-keys`, {
        openai_key: openaiKey || null,
        gemini_key: geminiKey || null
      });
      
      setKeyStatus(response.data);
      
      if (onConfigured) {
        onConfigured(response.data);
      }
      
      // Clear the input fields after successful save
      setOpenaiKey('');
      setGeminiKey('');
      
      // Close dialog if at least one key is configured
      if (response.data.openai_configured || response.data.gemini_configured) {
        setTimeout(() => onClose(), 500);
      }
    } catch (err) {
      setError('Failed to save API keys. Please try again.');
      console.error('Error saving API keys:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClearKeys = async () => {
    setLoading(true);
    try {
      await axios.delete(`${API_BASE}/api/clear-keys`);
      setKeyStatus({ openai_configured: false, gemini_configured: false });
      setOpenaiKey('');
      setGeminiKey('');
    } catch (err) {
      setError('Failed to clear API keys.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <SettingsIcon />
          <Typography variant="h6">Configure API Keys</Typography>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Enter your API keys to enable AI-powered features. Keys are stored locally and never shared.
          </Typography>

          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={12}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <Typography variant="subtitle1">OpenAI API Key</Typography>
                {keyStatus.openai_configured && (
                  <Chip
                    size="small"
                    icon={<CheckIcon />}
                    label="Configured"
                    color="success"
                    variant="outlined"
                  />
                )}
              </Box>
              <TextField
                fullWidth
                type={showOpenaiKey ? 'text' : 'password'}
                placeholder="sk-..."
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowOpenaiKey(!showOpenaiKey)}
                        edge="end"
                        size="small"
                      >
                        {showOpenaiKey ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                Get your key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer">OpenAI Platform</a>
              </Typography>
            </Grid>

            <Grid item xs={12}>
              <Box display="flex" alignItems="center" gap={1} mb={1}>
                <Typography variant="subtitle1">Google Gemini API Key</Typography>
                {keyStatus.gemini_configured && (
                  <Chip
                    size="small"
                    icon={<CheckIcon />}
                    label="Configured"
                    color="success"
                    variant="outlined"
                  />
                )}
              </Box>
              <TextField
                fullWidth
                type={showGeminiKey ? 'text' : 'password'}
                placeholder="AIza..."
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowGeminiKey(!showGeminiKey)}
                        edge="end"
                        size="small"
                      >
                        {showGeminiKey ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                Get your key from <a href="https://makersuite.google.com/app/apikey" target="_blank" rel="noopener noreferrer">Google AI Studio</a>
              </Typography>
            </Grid>
          </Grid>

          {(keyStatus.openai_configured || keyStatus.gemini_configured) && (
            <Alert severity="info" sx={{ mt: 2 }}>
              You have API keys configured. You can update them by entering new values above.
            </Alert>
          )}
        </Box>
      </DialogContent>
      
      <DialogActions>
        {(keyStatus.openai_configured || keyStatus.gemini_configured) && (
          <Button 
            onClick={handleClearKeys} 
            color="error"
            disabled={loading}
            sx={{ mr: 'auto' }}
          >
            Clear All Keys
          </Button>
        )}
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Button 
          onClick={handleSave} 
          variant="contained" 
          disabled={loading || (!openaiKey && !geminiKey)}
        >
          {loading ? 'Saving...' : 'Save Keys'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}