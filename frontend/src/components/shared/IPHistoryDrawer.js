import React, { useState, useEffect } from 'react';
import {
  Drawer, Box, Typography, IconButton, Divider, Chip, CircularProgress,
  LinearProgress, Table, TableBody, TableCell, TableHead, TableRow,
  Button, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions,
  RadioGroup, FormControlLabel, Radio, Select, MenuItem, FormControl, InputLabel,
  useTheme,
} from '@mui/material';
import {
  Close, Shield, Block, CheckCircle, Warning,
  Timeline, CalendarToday, Speed, OpenInNew,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import api, { getIPHistory } from '../../services/api';
import { iconSize } from '../../theme';
import { useLanguage } from '../../context/LanguageContext';
import { formatLocaleDate } from '../../utils/locale';

const DRAWER_WIDTH = 480;
const BLOCK_HOUR_OPTIONS = [1, 6, 24, 168];

function getRiskColor(score) {
  if (score < 30) return '#00e676';
  if (score <= 70) return '#ffd600';
  return '#ff1744';
}

function RiskScoreCard({ score, t }) {
  const color = getRiskColor(score);
  const riskLabel = score < 30 ? t('ipHistory.lowRisk') : score <= 70 ? t('ipHistory.mediumRisk') : t('ipHistory.highRisk');
  return (
    <Box sx={{
      p: 2, borderRadius: 2, border: `1px solid ${color}33`,
      bgcolor: `${color}11`, mb: 2, display: 'flex', alignItems: 'center', gap: 2,
    }}>
      <Box sx={{
        width: 56, height: 56, borderRadius: '50%',
        border: `3px solid ${color}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <Typography variant="h6" sx={{ fontWeight: 800, color, lineHeight: 1 }}>{score}</Typography>
      </Box>
      <Box>
        <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          {t('ipHistory.riskScore')}
        </Typography>
        <Typography variant="body2" sx={{ color, fontWeight: 700 }}>
          {riskLabel}
        </Typography>
      </Box>
    </Box>
  );
}

export default function IPHistoryDrawer({ ip, onClose, isAdmin = false }) {
  const theme = useTheme();
  const { t, language } = useLanguage();
  const sem = theme.semantic;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [blockDialogOpen, setBlockDialogOpen] = useState(false);
  const [blockType, setBlockType] = useState('permanent');
  const [blockHours, setBlockHours] = useState(24);
  const navigate = useNavigate();

  const refreshData = () => getIPHistory(ip, language).then((res) => setData(res.data));

  useEffect(() => {
    if (!ip) { setData(null); return; }
    setLoading(true);
    refreshData()
      .catch(() => toast.error(t('ipHistory.loadFailed')))
      .finally(() => setLoading(false));
  }, [ip, language]);

  const handleBlock = async () => {
    try {
      const body = {
        ip_address: ip,
        reason: `Manually blocked from IP history — Risk Score: ${data?.risk_score}`,
        block_type: blockType,
      };
      if (blockType === 'temporary') body.hours = blockHours;
      await api.post('/blocked-ips/', body);
      toast.success(`IP ${ip} blocked`);
      setBlockDialogOpen(false);
      await refreshData();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed to block IP');
    }
  };

  const handleWhitelist = async () => {
    try {
      await api.post('/blocked-ips/', {
        ip_address: ip,
        reason: 'Whitelisted from IP history',
        block_type: 'permanent',
        is_whitelist: true,
      });
      toast.success(`IP ${ip} whitelisted`);
      await refreshData();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed to whitelist IP');
    }
  };

  const formatDate = (iso) => {
    if (!iso) return '—';
    return formatLocaleDate(iso, language, {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const formatDateShort = (iso) => {
    if (!iso) return '—';
    return formatLocaleDate(iso, language, {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const severityColors = { critical: '#ff1744', high: '#ff6d00', medium: '#ffd600', low: '#00e676' };
  const surface = sem?.surfaceMuted;

  return (
    <>
      <Drawer
        anchor="right"
        open={!!ip}
        onClose={onClose}
        PaperProps={{
          sx: {
            width: DRAWER_WIDTH,
            bgcolor: 'background.paper',
            borderLeft: `1px solid ${theme.palette.divider}`,
            p: 0,
            display: 'flex',
            flexDirection: 'column',
          },
        }}
      >
        <Box sx={{
          px: 3, py: 2,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          borderBottom: `1px solid ${theme.palette.divider}`,
          bgcolor: 'background.default',
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Shield sx={{ color: 'primary.main', fontSize: iconSize.nav }} />
            <Box>
              <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '0.68rem' }}>
                {t('ipHistory.title')}
              </Typography>
              <Typography variant="h6" sx={{ fontFamily: 'monospace', fontWeight: 700, color: 'warning.main', lineHeight: 1.2 }}>
                {ip}
              </Typography>
            </Box>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {data && (
              data.is_blocked
                ? <Chip icon={<Block sx={{ fontSize: iconSize.dense }} />} label={t('ipHistory.blocked')} size="small" sx={{ bgcolor: sem.chipBlocked.bg, color: sem.chipBlocked.color, fontWeight: 700 }} />
                : data.is_whitelisted
                  ? <Chip icon={<CheckCircle sx={{ fontSize: iconSize.dense }} />} label={t('ipHistory.whitelisted')} size="small" sx={{ bgcolor: sem.alertSuccess.bg, color: sem.alertSuccess.color, fontWeight: 700 }} />
                  : <Chip icon={<Warning sx={{ fontSize: iconSize.dense }} />} label={t('ipHistory.active')} size="small" sx={{ bgcolor: sem.chipTemporary.bg, color: sem.chipTemporary.color, fontWeight: 700 }} />
            )}
            <IconButton onClick={onClose} size="small" sx={{ color: 'text.secondary' }}><Close /></IconButton>
          </Box>
        </Box>

        <Box sx={{ flex: 1, overflow: 'auto', p: 3 }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
              <CircularProgress />
            </Box>
          ) : !data ? null : data.total_incidents === 0 ? (
            <Box sx={{ textAlign: 'center', mt: 6, color: 'text.secondary' }}>
              <Shield sx={{ fontSize: 48, opacity: 0.3, mb: 2 }} />
              <Typography>{t('ipHistory.noIncidents')}</Typography>
            </Box>
          ) : (
            <>
              <RiskScoreCard score={data.risk_score} t={t} />

              <Box sx={{
                p: 2, borderRadius: 2,
                bgcolor: surface.bg,
                border: `1px solid ${surface.border}`,
                mb: 2,
              }}>
                <Typography variant="caption" sx={{ color: 'primary.main', textTransform: 'uppercase', fontWeight: 700, fontSize: '0.68rem', letterSpacing: '0.08em' }}>
                  {t('ipHistory.patternAnalysis')}
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.primary', mt: 0.5, lineHeight: 1.6 }}>
                  {data.pattern_summary}
                </Typography>
              </Box>

              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 1.5, mb: 2 }}>
                {[
                  { icon: <Timeline sx={{ fontSize: iconSize.inline }} />, label: t('ipHistory.totalIncidents'), value: data.total_incidents },
                  { icon: <Speed sx={{ fontSize: iconSize.inline }} />, label: t('ipHistory.freqPerDay'), value: data.frequency_per_day },
                  { icon: <CalendarToday sx={{ fontSize: iconSize.inline }} />, label: t('ipHistory.firstSeen'), value: formatDate(data.first_seen) },
                  { icon: <CalendarToday sx={{ fontSize: iconSize.inline }} />, label: t('ipHistory.lastSeen'), value: formatDate(data.last_seen) },
                ].map(stat => (
                  <Box key={stat.label} sx={{
                    p: 1.5, borderRadius: 2,
                    bgcolor: surface.bg,
                    border: `1px solid ${surface.border}`,
                  }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.secondary', mb: 0.5 }}>
                      {stat.icon}
                      <Typography variant="caption" sx={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                        {stat.label}
                      </Typography>
                    </Box>
                    <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
                      {stat.value}
                    </Typography>
                  </Box>
                ))}
              </Box>

              {data.top_attack_types.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', fontWeight: 700, fontSize: '0.68rem', letterSpacing: '0.08em' }}>
                    {t('ipHistory.topAttackTypes')}
                  </Typography>
                  <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {data.top_attack_types.map(item => {
                      const pct = Math.round((item.count / data.total_incidents) * 100);
                      return (
                        <Box key={item.attack_type}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.3 }}>
                            <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.primary', fontSize: '0.78rem' }}>
                              {item.attack_type.replace(/_/g, ' ')}
                            </Typography>
                            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                              {item.count}x ({pct}%)
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={pct}
                            sx={{
                              height: 6, borderRadius: 3,
                              bgcolor: surface.bg,
                              '& .MuiLinearProgress-bar': { bgcolor: 'warning.main', borderRadius: 3 },
                            }}
                          />
                        </Box>
                      );
                    })}
                  </Box>
                </Box>
              )}

              <Divider sx={{ my: 2 }} />

              <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', fontWeight: 700, fontSize: '0.68rem', letterSpacing: '0.08em' }}>
                {t('ipHistory.recentIncidents')}
              </Typography>
              <Box sx={{ mt: 1, border: `1px solid ${surface.border}`, borderRadius: 2, overflow: 'hidden' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ '& th': { bgcolor: surface.bg, py: 1 } }}>
                      <TableCell sx={{ color: 'text.secondary', fontSize: '0.68rem' }}>{t('ipHistory.date')}</TableCell>
                      <TableCell sx={{ color: 'text.secondary', fontSize: '0.68rem' }}>{t('ipHistory.type')}</TableCell>
                      <TableCell sx={{ color: 'text.secondary', fontSize: '0.68rem' }}>{t('ipHistory.severity')}</TableCell>
                      <TableCell sx={{ color: 'text.secondary', fontSize: '0.68rem' }}>{t('ipHistory.status')}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.recent_incidents.map(inc => (
                      <TableRow
                        key={inc.id}
                        hover
                        sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                        onClick={() => { navigate(`/incidents/${inc.id}`); onClose(); }}
                      >
                        <TableCell sx={{ fontSize: '0.75rem', whiteSpace: 'nowrap', color: 'text.secondary' }}>
                          {formatDateShort(inc.created_at)}
                        </TableCell>
                        <TableCell>
                          <Typography sx={{ fontFamily: 'monospace', fontSize: '0.7rem', color: 'primary.main' }} noWrap>
                            {inc.attack_type.replace(/_/g, ' ')}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={inc.severity}
                            size="small"
                            sx={{
                              height: 18, fontSize: '0.65rem',
                              color: severityColors[inc.severity],
                              bgcolor: `${severityColors[inc.severity]}22`,
                            }}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>{inc.status.replace('_', ' ')}</Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </>
          )}
        </Box>

        {data && (
          <Box sx={{
            px: 3, py: 2,
            borderTop: `1px solid ${theme.palette.divider}`,
            bgcolor: 'background.default',
            display: 'flex', gap: 1, flexWrap: 'wrap',
          }}>
            <Button
              size="small"
              variant="outlined"
              color="primary"
              startIcon={<OpenInNew sx={{ fontSize: iconSize.inline }} />}
              onClick={() => { navigate(`/incidents?search=${ip}`); onClose(); }}
              sx={{ fontSize: '0.78rem' }}
            >
              {t('ipHistory.viewAll')}
            </Button>

            {isAdmin && !data.is_blocked && (
              <Button
                size="small"
                variant="outlined"
                color="error"
                startIcon={<Block sx={{ fontSize: iconSize.inline }} />}
                onClick={() => setBlockDialogOpen(true)}
                sx={{ fontSize: '0.78rem' }}
              >
                {t('ipHistory.blockIp')}
              </Button>
            )}
            {isAdmin && !data.is_whitelisted && (
              <Button
                size="small"
                variant="outlined"
                color="success"
                startIcon={<CheckCircle sx={{ fontSize: iconSize.inline }} />}
                onClick={handleWhitelist}
                sx={{ fontSize: '0.78rem' }}
              >
                {t('ipHistory.whitelist')}
              </Button>
            )}
          </Box>
        )}
      </Drawer>

      <Dialog open={blockDialogOpen} onClose={() => setBlockDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{t('ipHistory.blockTitle', { ip })}</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <RadioGroup value={blockType} onChange={(e) => setBlockType(e.target.value)}>
            <FormControlLabel value="permanent" control={<Radio />} label={t('ipHistory.permanent')} />
            <FormControlLabel value="temporary" control={<Radio />} label={t('ipHistory.temporary')} />
          </RadioGroup>
          {blockType === 'temporary' && (
            <FormControl fullWidth size="small" sx={{ mt: 1 }}>
              <InputLabel>{t('ipHistory.duration')}</InputLabel>
              <Select value={blockHours} label={t('ipHistory.duration')} onChange={(e) => setBlockHours(e.target.value)}>
                {BLOCK_HOUR_OPTIONS.map(h => (
                  <MenuItem key={h} value={h}>{h === 168 ? '168 (7 days)' : `${h} hour${h > 1 ? 's' : ''}`}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBlockDialogOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" color="error" onClick={handleBlock}>{t('ipHistory.block')}</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
