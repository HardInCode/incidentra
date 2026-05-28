import React, { useEffect, useState, useRef } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography,
} from '@mui/material';
import { useLanguage } from '../../context/LanguageContext';

const TOKEN_WARN_BEFORE_MS = 5 * 60 * 1000;
const IDLE_TIMEOUT_MS = 15 * 60 * 1000; // 15 menit idle
const IDLE_WARN_BEFORE_MS = 60 * 1000; // 1 menit warning sebelum logout

function getTokenExpiry() {
  try {
    const token = localStorage.getItem('incidentra_token');
    if (!token) return null;
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload.exp ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

export default function SessionTimeoutWarning({ onLogout }) {
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [warningType, setWarningType] = useState(''); // 'token' atau 'idle'
  const lastActivityRef = useRef(Date.now());

  // Listen deteksi keaktifan user
  useEffect(() => {
    const handleActivity = () => {
      lastActivityRef.current = Date.now();
    };

    window.addEventListener('mousemove', handleActivity);
    window.addEventListener('keydown', handleActivity);
    window.addEventListener('click', handleActivity);
    window.addEventListener('scroll', handleActivity);

    return () => {
      window.removeEventListener('mousemove', handleActivity);
      window.removeEventListener('keydown', handleActivity);
      window.removeEventListener('click', handleActivity);
      window.removeEventListener('scroll', handleActivity);
    };
  }, []);

  useEffect(() => {
    const tick = () => {
      // 1. Cek Token Expiration (24 jam hard limit)
      const exp = getTokenExpiry();
      if (!exp) return;
      const tokenRemaining = exp - Date.now();

      if (tokenRemaining <= 0) {
        onLogout();
        window.location.href = '/login';
        return;
      }

      // 2. Cek Idle Expiration (inactivity)
      const idleTime = Date.now() - lastActivityRef.current;
      const idleRemaining = IDLE_TIMEOUT_MS - idleTime;

      if (idleRemaining <= 0) {
        onLogout();
        window.location.href = '/login';
        return;
      }

      // 3. Tentukan prioritas modal warning
      if (tokenRemaining <= TOKEN_WARN_BEFORE_MS) {
        setOpen(true);
        setWarningType('token');
        setSecondsLeft(Math.max(0, Math.floor(tokenRemaining / 1000)));
      } else if (idleRemaining <= IDLE_WARN_BEFORE_MS) {
        setOpen(true);
        setWarningType('idle');
        setSecondsLeft(Math.max(0, Math.floor(idleRemaining / 1000)));
      } else {
        setOpen(false);
        setWarningType('');
      }
    };

    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [onLogout]);

  const handleStayLoggedIn = () => {
    setOpen(false);
    if (warningType === 'idle') {
      // Reset waktu aktivitas terakhir
      lastActivityRef.current = Date.now();
    } else {
      // Token kadaluarsa: arahkan ke login ulang
      window.location.href = '/login';
    }
  };

  const mins = Math.floor(secondsLeft / 60);
  const secs = secondsLeft % 60;
  const formattedTime = `${mins}:${secs.toString().padStart(2, '0')}`;

  return (
    <Dialog open={open} maxWidth="xs" fullWidth>
      <DialogTitle>
        {warningType === 'token' ? t('session.tokenTitle') : t('session.idleTitle')}
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary">
          {warningType === 'token' 
            ? t('session.tokenBody', { time: formattedTime }) 
            : t('session.idleBody', { time: formattedTime })
          }
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onLogout} color="inherit">{t('session.logout')}</Button>
        <Button variant="contained" onClick={handleStayLoggedIn}>
          {warningType === 'token' ? t('session.signInAgain') : t('session.stayActive')}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
