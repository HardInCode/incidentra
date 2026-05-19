import React, { useState, useEffect } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, Button, Chip, Alert,
  Select, MenuItem, FormControl, InputLabel, IconButton, InputAdornment,
  FormControlLabel, Switch,
} from '@mui/material';
import {
  Visibility, VisibilityOff, Save, Settings as SettingsIcon, Palette, History, Notifications,
  VolumeUp,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useThemeMode } from '../context/ThemeContext';
import { useLanguage } from '../context/LanguageContext';
import useCurrentUser from '../hooks/useCurrentUser';
import { toast } from 'react-toastify';
import {
  getSettings, updateSettings, testNotification, testAbuseIPDB, testGroq,
} from '../services/api';
import {
  isNotificationSoundEnabled,
  setNotificationSoundEnabled,
  unlockNotificationSound,
  playNotificationSound,
} from '../utils/notificationSound';

const GROQ_MODELS = [
  'llama-3.3-70b-versatile',
  'llama-3.1-8b-instant',
  'meta-llama/llama-4-scout-17b-16e-instruct',
];

function ConfigBadge({ configured }) {
  const { t } = useLanguage();
  return (
    <Chip
      size="small"
      label={configured ? `● ${t('common.configured')}` : `○ ${t('common.notSet')}`}
      sx={{
        bgcolor: configured ? 'rgba(0,230,118,0.15)' : 'rgba(136,146,164,0.2)',
        color: configured ? '#00e676' : '#8892a4',
        fontWeight: 600,
        fontSize: '0.7rem',
      }}
    />
  );
}

const APPEARANCE_OPTIONS = [
  { value: 'dark', label: 'Dark' },
  { value: 'light', label: 'Light' },
  { value: 'system', label: 'System' },
];

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'id', label: 'Bahasa Indonesia' },
];

export default function Settings() {
  const { preference, setPreference } = useThemeMode();
  const { language, setLanguage, t } = useLanguage();
  const navigate = useNavigate();
  const currentUser = useCurrentUser();
  const isAdmin = currentUser?.role === 'admin';
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [edited, setEdited] = useState({});
  const [showKeys, setShowKeys] = useState({});
  const [testResults, setTestResults] = useState({ groq: null, abuseipdb: null, email: null, telegram: null });
  const [alertSound, setAlertSound] = useState(isNotificationSoundEnabled);

  const fetchSettings = async () => {
    try {
      const res = await getSettings();
      setSettings(res.data);
      setEdited({});
    } catch (e) {
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSettings(); }, []);

  const getValue = (key) => {
    if (edited[key] !== undefined) return edited[key];
    return settings?.[key]?.value ?? '';
  };

  const setValue = (key, value) => {
    setEdited((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {};
      for (const key of Object.keys(edited)) {
        const val = edited[key];
        if (val !== undefined && val !== '' && !val.includes('••••••')) {
          payload[key] = val;
        } else if (val === '') {
          payload[key] = '';
        }
      }
      await updateSettings(payload);
      toast.success('Settings saved successfully');
      fetchSettings();
    } catch (e) {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const runTest = async (name, fn) => {
    setTestResults((prev) => ({ ...prev, [name]: { loading: true } }));
    try {
      const res = await fn();
      setTestResults((prev) => ({
        ...prev,
        [name]: { success: true, message: res.data?.message ?? 'OK' },
      }));
    } catch (e) {
      setTestResults((prev) => ({
        ...prev,
        [name]: {
          success: false,
          error: e.response?.data?.error ?? e.response?.data?.errors?.join?.(', ') ?? e.message,
        },
      }));
    }
  };

  const toggleShow = (key) => {
    setShowKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const isPasswordField = (key) =>
    ['GROQ_API_KEY', 'ABUSEIPDB_API_KEY', 'SMTP_PASSWORD', 'TELEGRAM_BOT_TOKEN'].includes(key);

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}><Typography>{t('common.loading')}</Typography></Box>;
  if (!settings) return null;

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h4" sx={{ fontWeight: 800, color: 'primary.main' }}>{t('settings.title')}</Typography>
        <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
          {t('settings.subtitle')}
        </Typography>
      </Box>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Palette sx={{ color: 'primary.main' }} />
            <Typography variant="h6">{t('settings.appearance')}</Typography>
          </Box>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>{t('settings.theme')}</InputLabel>
              <Select
                value={preference}
                label={t('settings.theme')}
                onChange={(e) => setPreference(e.target.value)}
              >
                {APPEARANCE_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>{t('settings.language')}</InputLabel>
              <Select
                value={language}
                label={t('settings.language')}
                onChange={(e) => setLanguage(e.target.value)}
              >
                {LANGUAGE_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 1 }}>
            {t('settings.themeHint')}
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 0.5 }}>
            {t('settings.languageHint')}
          </Typography>
        </CardContent>
      </Card>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Notifications sx={{ color: 'primary.main' }} />
            <Typography variant="h6">{t('settings.alertsSection')}</Typography>
          </Box>
          <FormControlLabel
            control={(
              <Switch
                checked={alertSound}
                onChange={(e) => {
                  const on = e.target.checked;
                  setAlertSound(on);
                  setNotificationSoundEnabled(on);
                  if (on) {
                    unlockNotificationSound();
                    playNotificationSound();
                  }
                }}
              />
            )}
            label={t('settings.alertSound')}
          />
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mt: 0.5 }}>
            {t('settings.alertSoundHint')}
          </Typography>
          <Button
            variant="outlined"
            size="small"
            startIcon={<VolumeUp />}
            sx={{ mt: 2 }}
            onClick={() => {
              unlockNotificationSound();
              if (!playNotificationSound()) {
                toast.warn(t('settings.alertSoundBlocked'));
              }
            }}
          >
            {t('settings.testAlertSound')}
          </Button>
        </CardContent>
      </Card>

      {isAdmin && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <History sx={{ color: 'secondary.main' }} />
              <Typography variant="h6">{t('settings.auditSection')}</Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t('settings.auditHint')}
            </Typography>
            <Button variant="outlined" size="small" onClick={() => navigate('/audit')}>
              {t('settings.openAudit')}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Section 1 — AI Assistant (Groq) */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <SettingsIcon sx={{ color: '#7c4dff' }} />
            <Typography variant="h6">AI Assistant (Groq)</Typography>
            <ConfigBadge configured={settings.GROQ_API_KEY?.configured} />
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 400 }}>
            <TextField
              label={t('settings.groqKey')}
              type={showKeys.GROQ_API_KEY ? 'text' : 'password'}
              value={getValue('GROQ_API_KEY')}
              onChange={(e) => setValue('GROQ_API_KEY', e.target.value)}
              size="small"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => toggleShow('GROQ_API_KEY')} size="small">
                      {showKeys.GROQ_API_KEY ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <FormControl size="small" sx={{ minWidth: 280 }}>
              <InputLabel>{t('settings.model')}</InputLabel>
              <Select
                value={getValue('GROQ_MODEL') || GROQ_MODELS[0]}
                label={t('settings.model')}
                onChange={(e) => setValue('GROQ_MODEL', e.target.value)}
              >
                {GROQ_MODELS.map((m) => (
                  <MenuItem key={m} value={m}>{m}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              variant="outlined"
              size="small"
              onClick={() => runTest('groq', testGroq)}
              disabled={testResults.groq?.loading}
            >
              {testResults.groq?.loading ? t('settings.testing') : t('settings.testConnection')}
            </Button>
            {testResults.groq && !testResults.groq.loading && (
              <Alert severity={testResults.groq.success ? 'success' : 'error'} sx={{ mt: 1 }}>
                {testResults.groq.success ? testResults.groq.message : testResults.groq.error}
              </Alert>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Section 2 — AbuseIPDB */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Typography variant="h6">{t('settings.abuseTitle')}</Typography>
            <ConfigBadge configured={settings.ABUSEIPDB_API_KEY?.configured} />
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 400 }}>
            <TextField
              label={t('settings.abuseKey')}
              type={showKeys.ABUSEIPDB_API_KEY ? 'text' : 'password'}
              value={getValue('ABUSEIPDB_API_KEY')}
              onChange={(e) => setValue('ABUSEIPDB_API_KEY', e.target.value)}
              size="small"
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => toggleShow('ABUSEIPDB_API_KEY')} size="small">
                      {showKeys.ABUSEIPDB_API_KEY ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {t('settings.abuseHint')}
            </Typography>
            <Button
              variant="outlined"
              size="small"
              onClick={() => runTest('abuseipdb', testAbuseIPDB)}
              disabled={testResults.abuseipdb?.loading}
            >
              {testResults.abuseipdb?.loading ? t('settings.testing') : t('settings.testApiKey')}
            </Button>
            {testResults.abuseipdb && !testResults.abuseipdb.loading && (
              <Alert severity={testResults.abuseipdb.success ? 'success' : 'error'} sx={{ mt: 1 }}>
                {testResults.abuseipdb.success ? testResults.abuseipdb.message : testResults.abuseipdb.error}
              </Alert>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Section 3 — Email */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Typography variant="h6">{t('settings.emailTitle')}</Typography>
            <ConfigBadge configured={settings.SMTP_HOST?.configured} />
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 400 }}>
            <TextField label={t('settings.smtpHost')} size="small" value={getValue('SMTP_HOST')} onChange={(e) => setValue('SMTP_HOST', e.target.value)} />
            <TextField label={t('settings.smtpPort')} type="number" size="small" value={getValue('SMTP_PORT') || 587} onChange={(e) => setValue('SMTP_PORT', e.target.value)} />
            <TextField label={t('settings.username')} size="small" value={getValue('SMTP_USER')} onChange={(e) => setValue('SMTP_USER', e.target.value)} />
            <TextField
              label={t('settings.password')}
              type={showKeys.SMTP_PASSWORD ? 'text' : 'password'}
              size="small"
              value={getValue('SMTP_PASSWORD')}
              onChange={(e) => setValue('SMTP_PASSWORD', e.target.value)}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => toggleShow('SMTP_PASSWORD')} size="small">
                      {showKeys.SMTP_PASSWORD ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <TextField label={t('settings.alertEmail')} size="small" value={getValue('ALERT_EMAIL')} onChange={(e) => setValue('ALERT_EMAIL', e.target.value)} />
            <Button
              variant="outlined"
              size="small"
              onClick={() => runTest('email', () => testNotification('email'))}
              disabled={testResults.email?.loading}
            >
              {testResults.email?.loading ? t('settings.sending') : t('settings.sendTestEmail')}
            </Button>
            {testResults.email && !testResults.email.loading && (
              <Alert severity={testResults.email.success ? 'success' : 'error'} sx={{ mt: 1 }}>
                {testResults.email.success ? t('settings.testEmailOk') : testResults.email.error}
              </Alert>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Section 4 — Telegram */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <Typography variant="h6">{t('settings.telegramTitle')}</Typography>
            <ConfigBadge configured={settings.TELEGRAM_BOT_TOKEN?.configured} />
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 400 }}>
            <TextField
              label={t('settings.botToken')}
              type={showKeys.TELEGRAM_BOT_TOKEN ? 'text' : 'password'}
              size="small"
              value={getValue('TELEGRAM_BOT_TOKEN')}
              onChange={(e) => setValue('TELEGRAM_BOT_TOKEN', e.target.value)}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => toggleShow('TELEGRAM_BOT_TOKEN')} size="small">
                      {showKeys.TELEGRAM_BOT_TOKEN ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <TextField label={t('settings.chatId')} size="small" value={getValue('TELEGRAM_CHAT_ID')} onChange={(e) => setValue('TELEGRAM_CHAT_ID', e.target.value)} />
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {t('settings.telegramHint')}
            </Typography>
            <Button
              variant="outlined"
              size="small"
              onClick={() => runTest('telegram', () => testNotification('telegram'))}
              disabled={testResults.telegram?.loading}
            >
              {testResults.telegram?.loading ? t('settings.sending') : t('settings.sendTestMsg')}
            </Button>
            {testResults.telegram && !testResults.telegram.loading && (
              <Alert severity={testResults.telegram.success ? 'success' : 'error'} sx={{ mt: 1 }}>
                {testResults.telegram.success ? t('settings.testMsgOk') : testResults.telegram.error}
              </Alert>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Section 5 — Detection Thresholds */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>{t('settings.thresholds')}</Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 300 }}>
            <TextField
              label={t('settings.bruteForce')}
              type="number"
              size="small"
              value={getValue('BRUTE_FORCE_THRESHOLD') || 10}
              onChange={(e) => setValue('BRUTE_FORCE_THRESHOLD', e.target.value)}
              helperText={t('settings.bruteForceHint')}
            />
            <TextField
              label={t('settings.tempBlock')}
              type="number"
              size="small"
              value={getValue('TEMP_BLOCK_DURATION') ? Math.round(parseInt(getValue('TEMP_BLOCK_DURATION'), 10) / 3600) : 24}
              onChange={(e) => setValue('TEMP_BLOCK_DURATION', String(parseInt(e.target.value, 10) * 3600))}
              helperText={t('settings.tempBlockHint')}
            />
            <TextField
              label={t('settings.rateLimit')}
              type="number"
              size="small"
              value={getValue('RATE_LIMIT_WINDOW') || 60}
              onChange={(e) => setValue('RATE_LIMIT_WINDOW', e.target.value)}
            />
          </Box>
        </CardContent>
      </Card>

      <Button
        variant="contained"
        startIcon={saving ? null : <Save />}
        onClick={handleSave}
        disabled={saving || Object.keys(edited).length === 0}
        color="primary"
      >
        {saving ? t('common.saving') : t('common.save')}
      </Button>
    </Box>
  );
}
