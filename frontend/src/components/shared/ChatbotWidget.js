import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box, IconButton, Typography, TextField,
  CircularProgress, Chip, Divider, Tooltip, Drawer, useTheme,
} from '@mui/material';
import { Close, Send, Delete, AutoAwesome, OpenWith } from '@mui/icons-material';
import { sendChatMessage } from '../../services/api';
import { useLanguage } from '../../context/LanguageContext';
import { useChatbotContext } from '../../context/ChatbotContext';

const SESSION_ID = 'chatbot-' + Math.random().toString(36).slice(2);
const POS_STORAGE_KEY = 'sme_chatbot_pos';
const FAB_SIZE = 52;
const DRAG_THRESHOLD_PX = 6;

const QUICK_PROMPTS = [
  'Explain SQL Injection to a non-technical person',
  'Write a regex pattern to detect XSS attacks',
  'What should I do when I see a CRITICAL incident?',
  'How does brute force attack work?',
];

function loadSavedPosition() {
  try {
    const raw = localStorage.getItem(POS_STORAGE_KEY);
    if (!raw) return null;
    const { x, y } = JSON.parse(raw);
    if (Number.isFinite(x) && Number.isFinite(y)) return { x, y };
  } catch {
    /* ignore */
  }
  return null;
}

function defaultPosition() {
  return {
    x: Math.max(16, window.innerWidth - FAB_SIZE - 24),
    y: Math.max(16, window.innerHeight - FAB_SIZE - 24),
  };
}

function clampPosition(pos) {
  const maxX = window.innerWidth - FAB_SIZE - 8;
  const maxY = window.innerHeight - FAB_SIZE - 8;
  return {
    x: Math.min(Math.max(8, pos.x), maxX),
    y: Math.min(Math.max(8, pos.y), maxY),
  };
}

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

export default function ChatbotWidget() {
  const theme = useTheme();
  const { t } = useLanguage();
  const { incidentContext } = useChatbotContext();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [fabPos, setFabPos] = useState(() => loadSavedPosition() || defaultPosition());
  const messagesEndRef = useRef(null);
  const dragRef = useRef({ active: false, moved: false, offsetX: 0, offsetY: 0, startX: 0, startY: 0 });

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  useEffect(() => {
    const onResize = () => setFabPos((p) => clampPosition(p));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const onPointerMove = useCallback((e) => {
    if (!dragRef.current.active) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    if (Math.hypot(dx, dy) > DRAG_THRESHOLD_PX) {
      dragRef.current.moved = true;
    }
    setFabPos(clampPosition({
      x: e.clientX - dragRef.current.offsetX,
      y: e.clientY - dragRef.current.offsetY,
    }));
  }, []);

  const onPointerUp = useCallback(() => {
    if (!dragRef.current.active) return;
    dragRef.current.active = false;
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
    setFabPos((p) => {
      localStorage.setItem(POS_STORAGE_KEY, JSON.stringify(p));
      return p;
    });
  }, [onPointerMove]);

  const onFabPointerDown = (e) => {
    if (e.button !== 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    dragRef.current = {
      active: true,
      moved: false,
      offsetX: e.clientX - rect.left,
      offsetY: e.clientY - rect.top,
      startX: e.clientX,
      startY: e.clientY,
    };
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
  };

  const onFabClick = () => {
    if (dragRef.current.moved) {
      dragRef.current.moved = false;
      return;
    }
    setOpen(true);
  };

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
      <Tooltip title={t('chatbot.dragHint')} placement="left">
        <IconButton
          onPointerDown={onFabPointerDown}
          onClick={onFabClick}
          sx={{
            position: 'fixed',
            left: fabPos.x,
            top: fabPos.y,
            width: FAB_SIZE,
            height: FAB_SIZE,
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
            zIndex: 1200,
            cursor: 'grab',
            '&:active': { cursor: 'grabbing' },
            '&:hover': { bgcolor: 'primary.dark' },
            transition: 'background-color 0.2s',
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
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <OpenWith sx={{ fontSize: 12 }} /> {t('chatbot.dragHint')}
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
