import React, { useState, useRef, useEffect } from 'react';
import {
  Box, IconButton, Typography, TextField,
  CircularProgress, Chip, Divider, Tooltip, Drawer, useTheme,
} from '@mui/material';
import { Close, Send, Delete, AutoAwesome } from '@mui/icons-material';
import { sendChatMessage } from '../../services/api';

const SESSION_ID = 'chatbot-' + Math.random().toString(36).slice(2);

const QUICK_PROMPTS = [
  'Explain SQL Injection to a non-technical person',
  'Write a regex pattern to detect XSS attacks',
  'What should I do when I see a CRITICAL incident?',
  'How does brute force attack work?',
];

function TypingIndicator() {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, px: 2, py: 1 }}>
      {[0, 1, 2].map(i => (
        <Box key={i} sx={{
          width: 7, height: 7, borderRadius: '50%',
          bgcolor: 'secondary.main',
          animation: 'bounce 1.2s infinite',
          animationDelay: `${i * 0.2}s`,
          '@keyframes bounce': {
            '0%, 80%, 100%': { transform: 'scale(0.6)', opacity: 0.4 },
            '40%': { transform: 'scale(1)', opacity: 1 },
          },
        }} />
      ))}
      <Typography variant="caption" sx={{ color: 'text.secondary', ml: 0.5 }}>AI is thinking...</Typography>
    </Box>
  );
}

function Message({ msg }) {
  const theme = useTheme();
  const isUser = msg.role === 'user';
  return (
    <Box sx={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      mb: 1.5,
      px: 1.5,
    }}>
      {!isUser && (
        <Box
          component="img"
          src="/icons/chatbot.png"
          alt=""
          sx={{ width: 28, height: 28, borderRadius: '50%', mr: 1, flexShrink: 0, mt: 0.5, objectFit: 'contain' }}
        />
      )}
      <Box sx={{
        maxWidth: '80%',
        px: 2, py: 1.2,
        borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
        bgcolor: isUser ? 'action.selected' : 'action.hover',
        border: `1px solid ${theme.palette.divider}`,
      }}>
        <Typography variant="body2" sx={{
          color: 'text.primary',
          fontSize: '0.85rem',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          lineHeight: 1.6,
        }}>
          {msg.content}
        </Typography>
      </Box>
    </Box>
  );
}

export default function ChatbotWidget({ incidentContext = null }) {
  const theme = useTheme();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  const sendMessage = async (text) => {
    const msg = text || input.trim();
    if (!msg) return;
    setInput('');

    const userMsg = { role: 'user', content: msg };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await sendChatMessage({
        message: msg,
        context: incidentContext ? JSON.stringify(incidentContext) : '',
        session_id: SESSION_ID,
      });
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.reply }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Failed to get a response. Please check your API configuration.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => setMessages([]);

  return (
    <>
      <Tooltip title="AI Security Assistant" placement="left">
        <IconButton
          onClick={() => setOpen(true)}
          sx={{
            position: 'fixed',
            bottom: 80,
            right: 24,
            width: 52,
            height: 52,
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
            zIndex: 1300,
            '&:hover': { bgcolor: 'primary.dark' },
            transition: 'all 0.2s',
            p: 0,
            overflow: 'hidden',
          }}
        >
          <Box component="img" src="/icons/chatbot.png" alt="Chat" sx={{ width: 40, height: 40, objectFit: 'contain' }} />
        </IconButton>
      </Tooltip>

      <Drawer
        anchor="right"
        open={open}
        onClose={() => setOpen(false)}
        PaperProps={{
          sx: {
            width: 400,
            bgcolor: 'background.paper',
            display: 'flex',
            flexDirection: 'column',
            borderLeft: `1px solid ${theme.palette.divider}`,
          },
        }}
      >
        <Box sx={{
          px: 2, py: 1.5,
          bgcolor: 'background.default',
          borderBottom: `1px solid ${theme.palette.divider}`,
          display: 'flex', alignItems: 'center', gap: 1.5,
        }}>
          <Box component="img" src="/icons/chatbot.png" alt="" sx={{ width: 28, height: 28, objectFit: 'contain' }} />
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
              AI Security Assistant
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              Powered by Groq · SME-Guard
            </Typography>
          </Box>
          {messages.length > 0 && (
            <Tooltip title="Clear chat">
              <IconButton size="small" onClick={clearChat} sx={{ color: 'text.secondary' }}>
                <Delete sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
          )}
          <IconButton size="small" onClick={() => setOpen(false)} sx={{ color: 'text.secondary' }}>
            <Close sx={{ fontSize: 18 }} />
          </IconButton>
        </Box>

        {incidentContext && (
          <Box sx={{ px: 2, py: 1, bgcolor: 'action.hover', borderBottom: `1px solid ${theme.palette.divider}` }}>
            <Chip
              icon={<AutoAwesome sx={{ fontSize: 14 }} />}
              label={`Context: Incident #${incidentContext.id} — ${incidentContext.attack_type}`}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ fontSize: '0.72rem' }}
            />
          </Box>
        )}

        <Box sx={{ flex: 1, overflowY: 'auto', py: 2 }}>
          {messages.length === 0 && (
            <Box sx={{ px: 2 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2, textAlign: 'center', mt: 2 }}>
                Ask me anything about cybersecurity
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1, textTransform: 'uppercase', fontWeight: 700, fontSize: '0.68rem' }}>
                Quick Prompts
              </Typography>
              {QUICK_PROMPTS.map((p, i) => (
                <Box
                  key={i}
                  onClick={() => sendMessage(p)}
                  sx={{
                    p: 1.2, mb: 1, borderRadius: 2,
                    border: `1px solid ${theme.palette.divider}`,
                    bgcolor: 'action.hover',
                    cursor: 'pointer',
                    fontSize: '0.82rem',
                    color: 'text.secondary',
                    '&:hover': { bgcolor: 'action.selected', color: 'text.primary' },
                    transition: 'all 0.15s',
                  }}
                >
                  {p}
                </Box>
              ))}
            </Box>
          )}

          {messages.map((msg, i) => <Message key={i} msg={msg} />)}
          {loading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </Box>

        <Divider />

        <Box sx={{ p: 1.5, display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            size="small"
            placeholder="Ask about security incidents, attacks, regex patterns..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            sx={{ '& .MuiOutlinedInput-root': { borderRadius: 3, fontSize: '0.85rem' } }}
          />
          <IconButton
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            color="primary"
            sx={{ width: 38, height: 38, flexShrink: 0 }}
          >
            {loading ? <CircularProgress size={16} color="inherit" /> : <Send sx={{ fontSize: 18 }} />}
          </IconButton>
        </Box>
      </Drawer>
    </>
  );
}
