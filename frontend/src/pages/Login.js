/**
 * LOGIN & SELF-REGISTRATION PAGE
 * Ctrl+F: LOGIN_FLOW, FORGOT_PASSWORD_FLOW, handleLogin, handleRegister
 *
 * LOGIN_FLOW (hulu → hilir):
 *   handleLogin → api.login() → auth.py POST /login → JWT
 *   → onLogin(token) → App.js → localStorage incidentra_token → axios interceptor
 *
 * FORGOT_PASSWORD_FLOW:
 *   forgot mode → POST /auth/forgot-password → email link
 *   /reset-password?token=… → reset mode → POST /auth/reset-password
 *
 * Pasangan backend: backend/app/api/auth.py
 */
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Box, Card, CardContent, Typography, TextField, Button, CircularProgress, Alert, Link,
  IconButton, Tooltip,
} from '@mui/material';
import { HelpOutline } from '@mui/icons-material';
import { login, register, getSupportContact, forgotPassword, resetPassword } from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import { validatePassword } from '../utils/passwordPolicy';

const AUTH_ERROR_I18N = {
  invalid_credentials: 'login.invalidCredentials',
  account_pending: 'login.accountPending',
  account_suspended: 'login.accountSuspended',
  account_inactive: 'login.accountInactive',
  register_rate_limited: 'login.registerRateLimited',
  register_fields_required: 'login.registerFieldsRequired',
  password_too_short: 'login.passwordTooShort',
  password_policy_weak: 'login.passwordPolicyWeak',
  registerPasswordTooShortServer: 'login.passwordTooShort',
  username_exists: 'login.usernameExists',
  email_exists: 'login.emailExists',
  forgot_rate_limited: 'login.forgotRateLimited',
  forgot_email_required: 'login.forgotEmailRequired',
  reset_token_required: 'login.resetTokenInvalid',
  reset_token_invalid: 'login.resetTokenInvalid',
};

const FALLBACK_CONTACT_EMAIL = 'admin@incidentra.local';

function translateAuthError(err, t, fallbackKey, contactEmail) {
  const code = err.response?.data?.error;
  const i18nKey = code && AUTH_ERROR_I18N[code];
  if (i18nKey) return t(i18nKey, { email: contactEmail });
  return t(fallbackKey);
}

function passwordPolicyMessage(t, code) {
  if (code === 'password_too_short') return t('login.passwordTooShort');
  return t('login.passwordPolicyWeak');
}

export default function Login({ onLogin, initialMode = 'login' }) {
  const { t } = useLanguage();
  const [searchParams] = useSearchParams();
  const urlToken = (searchParams.get('token') || '').trim();

  const [mode, setMode] = useState(urlToken ? 'reset' : initialMode);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [contactEmail, setContactEmail] = useState(
    (process.env.REACT_APP_ADMIN_CONTACT_EMAIL || '').trim() || FALLBACK_CONTACT_EMAIL,
  );

  useEffect(() => {
    getSupportContact()
      .then((res) => {
        const email = (res.data?.email || '').trim();
        if (email) setContactEmail(email);
      })
      .catch(() => {
        /* keep build-time fallback */
      });
  }, []);

  useEffect(() => {
    if (urlToken) setMode('reset');
  }, [urlToken]);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');

  const [forgotEmail, setForgotEmail] = useState('');
  const [resetToken, setResetToken] = useState(urlToken);
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');

  useEffect(() => {
    if (urlToken) setResetToken(urlToken);
  }, [urlToken]);

  const clearError = () => {
    if (error) setError('');
  };

  const switchMode = (next) => {
    setMode(next);
    setError('');
    setInfo('');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await login(username, password);
      setError('');
      onLogin(res.data.token);
    } catch (err) {
      setError(translateAuthError(err, t, 'login.invalidCredentials', contactEmail));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (regPassword !== regConfirm) {
      setError(t('login.passwordMismatch'));
      return;
    }
    const policyErr = validatePassword(regPassword);
    if (policyErr) {
      setError(passwordPolicyMessage(t, policyErr));
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
      setError(translateAuthError(err, t, 'login.registerFailed', contactEmail));
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setError('');
    setInfo('');
    setLoading(true);
    try {
      const res = await forgotPassword(forgotEmail.trim());
      const devUrl = res.data?.dev_reset_url;
      setInfo(devUrl ? t('login.forgotSuccessDev', { url: devUrl }) : t('login.forgotSuccess'));
      setForgotEmail('');
    } catch (err) {
      setError(translateAuthError(err, t, 'login.forgotFailed', contactEmail));
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    if (newPassword !== newPasswordConfirm) {
      setError(t('login.passwordMismatch'));
      return;
    }
    const policyErr = validatePassword(newPassword);
    if (policyErr) {
      setError(passwordPolicyMessage(t, policyErr));
      return;
    }
    if (!resetToken.trim()) {
      setError(t('login.resetTokenInvalid'));
      return;
    }
    setLoading(true);
    try {
      await resetPassword({ token: resetToken.trim(), password: newPassword });
      setInfo(t('login.resetSuccess'));
      setNewPassword('');
      setNewPasswordConfirm('');
      setResetToken('');
      setMode('login');
    } catch (err) {
      setError(translateAuthError(err, t, 'login.resetFailed', contactEmail));
    } finally {
      setLoading(false);
    }
  };

  const titleKey = mode === 'register'
    ? 'login.registerTitle'
    : mode === 'forgot'
      ? 'login.forgotTitle'
      : mode === 'reset'
        ? 'login.resetTitle'
        : 'login.title';

  const subtitleKey = mode === 'register'
    ? 'login.registerSubtitle'
    : mode === 'forgot'
      ? 'login.forgotSubtitle'
      : mode === 'reset'
        ? 'login.resetSubtitle'
        : 'login.subtitle';

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
              href={`mailto:${contactEmail}?subject=${encodeURIComponent(t('login.contactAdminSubject'))}`}
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
            <Typography variant="h5" sx={{ fontWeight: 800, color: 'primary.main' }}>{t(titleKey)}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
              {t(subtitleKey)}
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

          {mode === 'login' && (
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
                  <Box sx={{ textAlign: 'right', mt: -0.5 }}>
                    <Link component="button" type="button" onClick={() => switchMode('forgot')} sx={{ fontSize: '0.85rem' }}>
                      {t('login.forgotLink')}
                    </Link>
                  </Box>
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
          )}

          {mode === 'register' && (
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

          {mode === 'forgot' && (
            <>
              <form onSubmit={handleForgotPassword}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    fullWidth
                    label={t('login.email')}
                    type="email"
                    value={forgotEmail}
                    onChange={e => { setForgotEmail(e.target.value); clearError(); }}
                    autoComplete="email"
                  />
                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    color="primary"
                    size="large"
                    disabled={loading || !forgotEmail.trim()}
                    sx={{ mt: 1, py: 1.5, fontWeight: 700 }}
                  >
                    {loading ? <CircularProgress size={24} color="inherit" /> : t('login.forgotSubmit')}
                  </Button>
                </Box>
              </form>

              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  <Link component="button" type="button" onClick={() => switchMode('login')} sx={{ fontWeight: 700 }}>
                    {t('login.backToSignIn')}
                  </Link>
                </Typography>
              </Box>
            </>
          )}

          {mode === 'reset' && (
            <>
              <form onSubmit={handleResetPassword}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {!urlToken && (
                    <TextField
                      fullWidth
                      label={t('login.resetTokenLabel')}
                      value={resetToken}
                      onChange={e => { setResetToken(e.target.value); clearError(); }}
                    />
                  )}
                  <TextField
                    fullWidth
                    label={t('login.newPassword')}
                    type="password"
                    value={newPassword}
                    onChange={e => { setNewPassword(e.target.value); clearError(); }}
                    autoComplete="new-password"
                    helperText={t('login.passwordHint')}
                  />
                  <TextField
                    fullWidth
                    label={t('login.confirmPassword')}
                    type="password"
                    value={newPasswordConfirm}
                    onChange={e => { setNewPasswordConfirm(e.target.value); clearError(); }}
                    autoComplete="new-password"
                  />
                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    color="primary"
                    size="large"
                    disabled={loading || !newPassword || !newPasswordConfirm || (!urlToken && !resetToken.trim())}
                    sx={{ mt: 1, py: 1.5, fontWeight: 700 }}
                  >
                    {loading ? <CircularProgress size={24} color="inherit" /> : t('login.resetSubmit')}
                  </Button>
                </Box>
              </form>

              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  <Link component="button" type="button" onClick={() => switchMode('login')} sx={{ fontWeight: 700 }}>
                    {t('login.backToSignIn')}
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
