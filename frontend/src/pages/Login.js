import React, { useState } from 'react';
import { Box, Card, CardContent, Typography, TextField, Button, CircularProgress, Alert } from '@mui/material';
import { login } from '../services/api';
import { useLanguage } from '../context/LanguageContext';

export default function Login({ onLogin }) {
  const { t } = useLanguage();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await login(username, password);
      setError('');
      onLogin(res.data.token);
    } catch (err) {
      setError(err.response?.data?.error || t('login.invalidCredentials'));
    } finally {
      setLoading(false);
    }
  };

  const clearError = () => {
    if (error) setError('');
  };

  return (
    <Box sx={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      bgcolor: 'background.default',
    }}>
      <Card sx={{ width: '100%', maxWidth: 420, mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Box
              component="img"
              src="/icons/smeguard.png"
              alt={t('brand.full')}
              sx={{ width: 64, height: 64, borderRadius: 3, mb: 2, objectFit: 'contain' }}
            />
            <Typography variant="h5" sx={{ fontWeight: 800, color: 'primary.main' }}>{t('login.title')}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
              {t('login.subtitle')}
            </Typography>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleLogin}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                fullWidth label={t('login.username')}
                value={username}
                onChange={e => { setUsername(e.target.value); clearError(); }}
                autoComplete="username"
              />
              <TextField
                fullWidth label={t('login.password')}
                type="password"
                value={password}
                onChange={e => { setPassword(e.target.value); clearError(); }}
                autoComplete="current-password"
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                color="primary"
                size="large"
                disabled={loading || !username || !password}
                sx={{ mt: 1, py: 1.5, fontWeight: 700 }}
              >
                {loading ? <CircularProgress size={24} color="inherit" /> : t('login.signIn')}
              </Button>
            </Box>
          </form>

          <Box sx={{ mt: 3, p: 2, bgcolor: 'action.hover', borderRadius: 2 }}>
            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
              {t('login.defaultCreds')}
            </Typography>
            <Typography variant="caption" sx={{ color: 'primary.main', fontFamily: 'monospace' }}>
              admin / Admin@Incidentra2026!<br />
              analyst / Analyst@Incidentra2026!
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
