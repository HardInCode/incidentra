/**
 * LOGIN & SELF-REGISTRATION PAGE
 * Ctrl+F: handleLogin, handleRegister, mode, AUTH_ERROR_I18N
 *
 * Alur login (hulu → hilir):
 *   Login.js handleLogin → api.js login() → auth.py POST /login → JWT
 *   → onLogin(token) → App.js handleLogin → localStorage → Dashboard
 *
 * Backend counterpart: backend/app/api/auth.py
 */
import React, { useState } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, Button, CircularProgress, Alert, Link,
  IconButton, Tooltip,
} from '@mui/material';
import { HelpOutline } from '@mui/icons-material';
import { login, register } from '../services/api';
import { useLanguage } from '../context/LanguageContext';

// Map kode error backend (auth.py) → key i18n — alert mengikuti bahasa app (en/id)
const AUTH_ERROR_I18N = {
  invalid_credentials: 'login.invalidCredentials',
  account_pending: 'login.accountPending',
  account_suspended: 'login.accountSuspended',
  account_inactive: 'login.accountInactive',
  register_rate_limited: 'login.registerRateLimited',
  register_fields_required: 'login.registerFieldsRequired',
  register_password_too_short: 'login.registerPasswordTooShortServer',
  username_exists: 'login.usernameExists',
  email_exists: 'login.emailExists',
};

const ADMIN_CONTACT_EMAIL = (
  process.env.REACT_APP_ADMIN_CONTACT_EMAIL || 'admin@incidentra.local'
).trim();

function translateAuthError(err, t, fallbackKey) {
  const code = err.response?.data?.error;
  const i18nKey = code && AUTH_ERROR_I18N[code];
  if (i18nKey) return t(i18nKey, { email: ADMIN_CONTACT_EMAIL });
  return t(fallbackKey);
}

export default function Login({ onLogin }) {
  const { t } = useLanguage();
  const [mode, setMode] = useState('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  // State form login
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // State form register
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');

  const clearError = () => {
    if (error) setError('');
  };

  const switchMode = (next) => {
    setMode(next);
    setError('');
    setInfo('');
  };

  // ─── Login: POST /api/auth/login ───
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await login(username, password);
      setError('');
      // onLogin = prop dari App.js → simpan JWT + setIsAuthenticated(true)
      onLogin(res.data.token);
    } catch (err) {
      setError(translateAuthError(err, t, 'login.invalidCredentials'));
    } finally {
      setLoading(false);
    }
  };

  // ─── Register: validasi frontend dulu, lalu POST /api/auth/register ───
  // confirmPassword cuma dicek di sini — backend tidak terima field itu
  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (regPassword !== regConfirm) {
      setError(t('login.passwordMismatch'));
      return;
    }
    if (regPassword.length < 8) {
      setError(t('login.passwordTooShort'));
      return;
    }
    setLoading(true);
    try {
      await register({ username: regUsername, email: regEmail, password: regPassword });
      setInfo(t('login.registerSuccess'));
      setRegUsername('');
      setRegEmail('');
      setRegPassword('');
      setRegConfirm('');
      setMode('login');
    } catch (err) {
      setError(translateAuthError(err, t, 'login.registerFailed'));
    } finally {
      setLoading(false);
    }
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
        <CardContent sx={{ p: 4, position: 'relative' }}>
          <Tooltip title={t('login.contactAdminTooltip')} arrow>
            <IconButton
              component="a"
              href={`mailto:${ADMIN_CONTACT_EMAIL}?subject=${encodeURIComponent(t('login.contactAdminSubject'))}`}
              aria-label={t('login.contactAdminTooltip')}
              size="small"
              sx={{
                position: 'absolute',
                top: 12,
                right: 12,
                color: 'text.secondary',
                '&:hover': { color: 'primary.main' },
              }}
            >
              <HelpOutline fontSize="small" />
            </IconButton>
          </Tooltip>

          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Box
              component="img"
              src="/icons/incidentra.png"
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
          {info && (
            <Alert severity="success" sx={{ mb: 2 }} onClose={() => setInfo('')}>
              {info}
            </Alert>
          )}

          {mode === 'login' ? (
            <>
              <form onSubmit={handleLogin}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    fullWidth
                    label={t('login.username')}
                    value={username}
                    onChange={e => { setUsername(e.target.value); clearError(); }}
                    autoComplete="username"
                  />
                  <TextField
                    fullWidth
                    label={t('login.password')}
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

              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  {t('login.noAccountPrompt')}{' '}
                  <Link component="button" type="button" onClick={() => switchMode('register')} sx={{ fontWeight: 700 }}>
                    {t('login.registerLink')}
                  </Link>
                </Typography>
              </Box>
            </>
          ) : (
            <>
              <form onSubmit={handleRegister}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    fullWidth
                    label={t('login.username')}
                    value={regUsername}
                    onChange={e => { setRegUsername(e.target.value); clearError(); }}
                    autoComplete="username"
                  />
                  <TextField
                    fullWidth
                    label={t('login.email')}
                    type="email"
                    value={regEmail}
                    onChange={e => { setRegEmail(e.target.value); clearError(); }}
                    autoComplete="email"
                  />
                  <TextField
                    fullWidth
                    label={t('login.password')}
                    type="password"
                    value={regPassword}
                    onChange={e => { setRegPassword(e.target.value); clearError(); }}
                    autoComplete="new-password"
                    helperText={t('login.passwordHint')}
                  />
                  <TextField
                    fullWidth
                    label={t('login.confirmPassword')}
                    type="password"
                    value={regConfirm}
                    onChange={e => { setRegConfirm(e.target.value); clearError(); }}
                    autoComplete="new-password"
                  />
                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    color="primary"
                    size="large"
                    disabled={loading || !regUsername || !regEmail || !regPassword || !regConfirm}
                    sx={{ mt: 1, py: 1.5, fontWeight: 700 }}
                  >
                    {loading ? <CircularProgress size={24} color="inherit" /> : t('login.registerButton')}
                  </Button>
                </Box>
              </form>

              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
                  {t('login.registerHint')}
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  {t('login.haveAccountPrompt')}{' '}
                  <Link component="button" type="button" onClick={() => switchMode('login')} sx={{ fontWeight: 700 }}>
                    {t('login.signIn')}
                  </Link>
                </Typography>
              </Box>
            </>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
