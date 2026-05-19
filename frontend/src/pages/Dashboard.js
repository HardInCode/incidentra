import React, { useState, useEffect } from 'react';
import {
  Box, Grid, Card, CardContent, CardActionArea, Typography, CircularProgress,
  Chip, Button, IconButton, Tooltip, LinearProgress, useTheme,
} from '@mui/material';
import {
  Security, Block, CheckCircle, Warning, Error as ErrorIcon,
  Refresh, TrendingUp, BugReport, Speed,
} from '@mui/icons-material';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  ArcElement, LineElement, PointElement, Tooltip as ChartTooltip,
  Legend, Filler,
} from 'chart.js';
import { getDashboardStats, getLogStatus } from '../services/api';
import { iconSize } from '../theme';
import { SeverityChip, AttackTypeChip } from '../components/shared/Chips';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';
import { formatLocaleDate, formatChartDay } from '../utils/locale';

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, LineElement, PointElement, ChartTooltip, Legend, Filler);

const REFRESH_INTERVAL = parseInt(process.env.REACT_APP_REFRESH_INTERVAL || '15000');

function StatCard({ title, value, icon, color, subtitle, onClick, clickHint }) {
  const body = (
    <CardContent sx={{ p: 3, height: '100%' }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <Box>
          <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
            {title}
          </Typography>
          <Typography variant="h3" sx={{ fontWeight: 800, color, mt: 0.5, lineHeight: 1.1 }}>
            {value ?? '—'}
          </Typography>
          {subtitle && (
            <Typography variant="caption" sx={{ color: 'text.secondary', mt: 0.5, display: 'block' }}>
              {subtitle}
            </Typography>
          )}
        </Box>
        <Box sx={{
          width: 48, height: 48, borderRadius: 3,
          bgcolor: `${color}22`, display: 'flex',
          alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          {React.cloneElement(icon, { sx: { color, fontSize: iconSize.nav } })}
        </Box>
      </Box>
    </CardContent>
  );

  if (!onClick) {
    return <Card sx={{ height: '100%' }}>{body}</Card>;
  }

  return (
    <Tooltip title={clickHint || ''} placement="top">
      <Card
        sx={{
          height: '100%',
          transition: 'border-color 0.2s, box-shadow 0.2s',
          border: '1px solid transparent',
          '&:hover': {
            borderColor: `${color}55`,
            boxShadow: `0 4px 20px ${color}22`,
          },
        }}
      >
        <CardActionArea onClick={onClick} sx={{ height: '100%' }}>
          {body}
        </CardActionArea>
      </Card>
    </Tooltip>
  );
}

function SystemStatusBanner({ status, t }) {
  const theme = useTheme();
  if (!status) return null;
  const sem = theme.semantic;
  const configs = {
    normal:   { ...sem.alertSuccess, icon: <CheckCircle /> },
    warning:  { ...sem.alertWarning, icon: <Warning /> },
    critical: { ...sem.alertError, icon: <ErrorIcon /> },
  };
  const statusLabels = {
    critical: t('dashboard.statusCritical'),
    warning: t('dashboard.statusWarning'),
    normal: t('dashboard.statusNormal'),
  };
  const c = configs[status.status] || configs.normal;
  const label = statusLabels[status.status] || status.label;
  return (
    <Box sx={{
      display: 'flex', alignItems: 'center', gap: 1.5, p: 2, borderRadius: 2,
      bgcolor: c.bg, border: `1px solid ${c.border}`, mb: 3,
    }}>
      {React.cloneElement(c.icon, { sx: { color: c.color, fontSize: iconSize.inline } })}
      <Typography sx={{ color: c.color, fontWeight: 700, fontSize: '0.9rem' }}>
        {t('dashboard.systemStatus', { label })}
      </Typography>
      {status.status === 'critical' && (
        <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: '#ff1744', ml: 'auto', animation: 'pulse 1s infinite' }} />
      )}
    </Box>
  );
}

const SEV_LINE_COLORS = { critical: '#ff1744', high: '#ff6d00', medium: '#ffd600', low: '#00e676' };

/** Integer Y/X scale for low incident counts — avoids Chart.js zooming to 1.85–2.10 on flat data. */
function countScale(tickColor, gridColor, values = []) {
  const max = values.length ? Math.max(...values, 0) : 0;
  return {
    beginAtZero: true,
    grid: { color: gridColor },
    suggestedMax: Math.max(5, max + 1),
    ticks: {
      color: tickColor,
      stepSize: 1,
      precision: 0,
    },
  };
}

function linePointStyle(counts, color, { fill = false } = {}) {
  const sparse = (counts || []).filter((c) => c > 0).length <= 2;
  return {
    borderColor: color,
    backgroundColor: fill ? `${color}22` : color,
    fill,
    tension: 0.35,
    spanGaps: false,
    pointBackgroundColor: color,
    pointBorderColor: color,
    pointRadius: sparse ? 6 : 4,
    pointHoverRadius: sparse ? 8 : 5,
    borderWidth: 2,
  };
}

export default function Dashboard() {
  const theme = useTheme();
  const { t, language } = useLanguage();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [logStale, setLogStale] = useState(false);
  const navigate = useNavigate();

  const fetchStats = async () => {
    try {
      const res = await getDashboardStats();
      setStats(res.data);
      setLastRefresh(new Date());
    } catch (e) {
      console.error('Dashboard stats error:', e);
    } finally {
      setLoading(false);
    }
  };

  // BUG 2 FIX: Check if log monitor is receiving data
  const checkLogStatus = async () => {
    try {
      const res = await getLogStatus();
      setLogStale(res.data.stale === true);
    } catch {
      // silently ignore
    }
  };

  useEffect(() => {
    fetchStats();
    checkLogStatus();
    const interval = setInterval(fetchStats, REFRESH_INTERVAL);
    const logInterval = setInterval(checkLogStatus, 30000);
    return () => { clearInterval(interval); clearInterval(logInterval); };
  }, []);

  if (loading) return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}>
      <CircularProgress color="primary" />
    </Box>
  );

  const chartDefaults = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } };
  const isDark = theme.palette.mode === 'dark';
  const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
  const tickColor = theme.palette.text.secondary;

  const timelineCounts = stats?.timeline?.map((t) => t.count) || [];
  const timelineLabels = stats?.timeline?.map((t) => formatChartDay(t.date, language)) || [];
  const timelineData = {
    labels: timelineLabels,
    datasets: [{
      label: 'Incidents',
      data: timelineCounts,
      ...linePointStyle(timelineCounts, '#00d4aa', { fill: true }),
    }],
  };

  const attackCounts = stats?.attack_breakdown?.map((a) => a.count) || [];
  const attackData = {
    labels: stats?.attack_breakdown?.map(a => a.type.replace(/_/g, ' ')) || [],
    datasets: [{
      data: attackCounts,
      backgroundColor: ['#ff1744','#ff6d00','#ffd600','#7c4dff','#00b0ff','#00e676'],
      borderWidth: 0,
    }],
  };

  const severityData = {
    labels: stats?.severity_breakdown?.map(s => s.severity) || [],
    datasets: [{
      data: stats?.severity_breakdown?.map(s => s.count) || [],
      backgroundColor: stats?.severity_breakdown?.map(s => SEV_LINE_COLORS[s.severity]) || [],
      borderWidth: 0,
    }],
  };

  const severityDates = (stats?.timeline || []).map((t) => t.date);
  const severityTrendData = {
    labels: severityDates.map((d) => formatChartDay(d, language)),
    datasets: ['critical', 'high', 'medium', 'low'].map((sev) => {
      const data = severityDates.map((d) => {
        const row = stats?.severity_timeline?.find((r) => r.date === d && r.severity === sev);
        return row?.count || 0;
      });
      return {
        label: sev.charAt(0).toUpperCase() + sev.slice(1),
        data,
        ...linePointStyle(data, SEV_LINE_COLORS[sev]),
      };
    }),
  };

  const severityTrendCounts = (stats?.severity_timeline || []).map((r) => r.count);

  return (
    <Box>
      {/* BUG 2 FIX: Warning banner if no log data in 60s */}
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 3, gap: 2 }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>{t('dashboard.title')}</Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.5 }}>
            {t('dashboard.lastUpdated', { time: formatLocaleDate(lastRefresh.toISOString(), language, { hour: '2-digit', minute: '2-digit', second: '2-digit' }) })}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
          {logStale && (
            <Tooltip title={t('dashboard.logWarningBody')} arrow placement="bottom-end">
              <Box sx={{
                px: 1.25,
                py: 0.5,
                borderRadius: 1,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 0.75,
                maxWidth: { xs: 160, sm: 280 },
                bgcolor: theme.semantic.alertWarning.bg,
                border: `1px solid ${theme.semantic.alertWarning.border}`,
                cursor: 'help',
              }}
              >
                <Warning sx={{ color: theme.semantic.alertWarning.color, fontSize: 16, flexShrink: 0 }} />
                <Typography
                  variant="caption"
                  noWrap
                  sx={{ color: theme.semantic.alertWarning.color, fontWeight: 500 }}
                >
                  {t('dashboard.logWarningShort')}
                </Typography>
              </Box>
            </Tooltip>
          )}
          <Tooltip title={t('common.refresh')}>
            <IconButton onClick={fetchStats} sx={{ color: 'primary.main' }}>
              <Refresh />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* System Status */}
      <SystemStatusBanner status={stats?.system_status} t={t} />

      {/* Stat Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}>
          <StatCard
            title={t('dashboard.totalIncidents')}
            value={stats?.total_incidents}
            icon={<Security />}
            color="#00d4aa"
            subtitle={t('dashboard.allTime')}
            onClick={() => navigate('/incidents/all')}
            clickHint={t('dashboard.goAllIncidents')}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title={t('dashboard.last24h')}
            value={stats?.last_24h}
            icon={<BugReport />}
            color="#ff6d00"
            subtitle={t('dashboard.newDetections')}
            onClick={() => navigate('/incidents/all')}
            clickHint={t('dashboard.goAllIncidents')}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title={t('dashboard.blockedIps')}
            value={stats?.blocked_ips}
            icon={<Block />}
            color="#ff1744"
            subtitle={t('dashboard.activeBlocks')}
            onClick={() => navigate('/blocked-ips')}
            clickHint={t('dashboard.goBlockedIps')}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title={t('dashboard.mttr')}
            value={stats?.mttr_minutes ? `${stats.mttr_minutes}m` : '—'}
            icon={<Speed />}
            color="#7c4dff"
            subtitle={t('dashboard.mttrSub')}
          />
        </Grid>
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>{t('dashboard.timeline')}</Typography>
              <Box sx={{ height: 220 }}>
                <Line data={timelineData} options={{
                  ...chartDefaults,
                  plugins: { ...chartDefaults.plugins, legend: { display: false } },
                  scales: {
                    x: { grid: { color: gridColor }, ticks: { color: tickColor } },
                    y: countScale(tickColor, gridColor, timelineCounts),
                  },
                }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>{t('dashboard.bySeverity')}</Typography>
              <Box sx={{ height: 180, display: 'flex', justifyContent: 'center' }}>
                <Doughnut data={severityData} options={{
                  ...chartDefaults,
                  plugins: { ...chartDefaults.plugins, legend: { display: true, position: 'bottom', labels: { color: tickColor, padding: 10, font: { size: 11 } } } },
                  cutout: '65%',
                }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>{t('dashboard.severityTrend')}</Typography>
              <Box sx={{ height: 220 }}>
                <Line
                  data={severityTrendData}
                  options={{
                    ...chartDefaults,
                    plugins: {
                      legend: {
                        display: true,
                        position: 'bottom',
                        labels: { color: tickColor, padding: 12, font: { size: 11 } },
                      },
                    },
                    scales: {
                      x: { grid: { color: gridColor }, ticks: { color: tickColor, maxRotation: 45 } },
                      y: countScale(tickColor, gridColor, severityTrendCounts),
                    },
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Attack breakdown + Top IPs */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>{t('dashboard.attackTypes')}</Typography>
              <Box sx={{ height: 200 }}>
                <Bar data={attackData} options={{
                  ...chartDefaults,
                  indexAxis: 'y',
                  scales: {
                    x: countScale(tickColor, gridColor, attackCounts),
                    y: { grid: { display: false }, ticks: { color: tickColor } },
                  },
                }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">{t('dashboard.topIps')}</Typography>
                <Button size="small" onClick={() => navigate('/incidents')} sx={{ color: 'primary.main' }}>
                  {t('common.viewAll')}
                </Button>
              </Box>
              {stats?.top_attacking_ips?.slice(0, 6).map((item, i) => (
                <Box key={item.ip} sx={{ mb: 1.5 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', color: '#ff6d00' }}>
                      {item.ip}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      {t('dashboard.incidentCount', { count: item.count })}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(100, (item.count / (stats.top_attacking_ips[0]?.count || 1)) * 100)}
                    sx={{ height: 4, borderRadius: 2, bgcolor: 'rgba(255,109,0,0.15)', '& .MuiLinearProgress-bar': { bgcolor: '#ff6d00' } }}
                  />
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
