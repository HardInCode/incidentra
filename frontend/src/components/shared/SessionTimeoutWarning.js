import React, { useEffect, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography,
} from '@mui/material';

const WARN_BEFORE_MS = 5 * 60 * 1000;

function getTokenExpiry() {
  try {
    const token = localStorage.getItem('sme_token');
    if (!token) return null;
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.exp ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

export default function SessionTimeoutWarning({ onLogout }) {
  const [open, setOpen] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);

  useEffect(() => {
    const tick = () => {
      const exp = getTokenExpiry();
      if (!exp) return;
      const remaining = exp - Date.now();
      if (remaining <= 0) {
        onLogout();
        window.location.href = '/login';
        return;
      }
      if (remaining <= WARN_BEFORE_MS) {
        setOpen(true);
        setSecondsLeft(Math.max(0, Math.floor(remaining / 1000)));
      } else {
        setOpen(false);
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [onLogout]);

  const handleStayLoggedIn = () => {
    setOpen(false);
    window.location.href = '/login';
  };

  const mins = Math.floor(secondsLeft / 60);
  const secs = secondsLeft % 60;

  return (
    <Dialog open={open} maxWidth="xs" fullWidth>
      <DialogTitle>Session expiring soon</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary">
          Your session will expire in{' '}
          <strong>{mins}:{secs.toString().padStart(2, '0')}</strong>.
          Sign in again to stay logged in.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onLogout} color="inherit">Log out</Button>
        <Button variant="contained" onClick={handleStayLoggedIn}>Sign in again</Button>
      </DialogActions>
    </Dialog>
  );
}
