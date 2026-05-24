import React, { useState, useCallback, useEffect, useMemo } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, Table, TableBody, TableCell, TableHead, TableRow,
  Chip, IconButton, ToggleButton, ToggleButtonGroup, Select, MenuItem, FormControl, InputLabel, Alert,
  FormControlLabel, Checkbox, Tooltip,
} from '@mui/material';
import {
  Wifi, Pause, PlayArrow, Refresh, BugReport, Warning, Block, CheckCircle, InfoOutlined,
} from '@mui/icons-material';
import { getRecentTraffic } from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import { formatLogTime, parseNginxLogTime } from '../utils/locale';

const TAG_COLORS = {
  attack: '#ff4444',
  suspicious: '#ffaa00',
  blocked: '#ff6d00',
  normal: '#00d4aa',
};

const TAG_ICONS = {
  attack: <BugReport sx={{ fontSize: 14 }} />,
  suspicious: <Warning sx={{ fontSize: 14 }} />,
  blocked: <Block sx={{ fontSize: 14 }} />,
  normal: <CheckCircle sx={{ fontSize: 14 }} />,
};

const METHOD_COLORS = {
  GET: '#00d4aa',
  POST: '#7c4dff',
  DELETE: '#ff4444',
  PUT: '#ffaa00',
};

function getStatusColor(status) {
  if (status >= 500) return '#ff4444';
  if (status >= 400) return '#ffaa00';
  return '#00d4aa';
}

export default function LiveTraffic() {
  const { t, language } = useLanguage();
  const [data, setData] = useState({ entries: [], summary: {}, total_lines: 0, log_path: null, error: null });
  const [loading, setLoading] = useState(true);
  const [paused, setPaused] = useState(false);
  const [search, setSearch] = useState('');
  const [tagFilter, setTagFilter] = useState('all');
  const [rowCount, setRowCount] = useState(100);
  const [sortDir, setSortDir] = useState('desc');
  const [hideStatic, setHideStatic] = useState(true);

  const fetchTraffic = useCallback(async () => {
    if (paused) return;
    try {
      const res = await getRecentTraffic(rowCount);
      setData(res.data);
    } catch (e) {
      setData({ entries: [], error: t('traffic.loadError') });
    } finally {
      setLoading(false);
    }
  }, [paused, rowCount]);

  useEffect(() => {
    fetchTraffic();
  }, [fetchTraffic]);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(fetchTraffic, 3000);
    return () => clearInterval(interval);
  }, [fetchTraffic, paused]);

  const isStaticAsset = (path) => (
    (path || '').startsWith('/static/')
    || path === '/favicon.ico'
  );

  const filtered = useMemo(() => {
    const list = (data.entries || []).filter((e) => {
      if (hideStatic && isStaticAsset(e.path)) return false;
      if (tagFilter !== 'all' && e.tag !== tagFilter) return false;
      if (!search) return true;
      const s = search.toLowerCase();
      return (
        (e.ip || '').toLowerCase().includes(s) ||
        (e.path || '').toLowerCase().includes(s) ||
        (e.query || '').toLowerCase().includes(s) ||
        (e.ua || '').toLowerCase().includes(s)
      );
    });
    return [...list].sort((a, b) => {
      const ta = parseNginxLogTime(a.time)?.getTime() || 0;
      const tb = parseNginxLogTime(b.time)?.getTime() || 0;
      const diff = tb - ta;
      return sortDir === 'desc' ? diff : -diff;
    });
  }, [data.entries, tagFilter, search, sortDir, hideStatic]);

  const toggleTagFilter = (tag) => {
    setTagFilter((prev) => (prev === tag ? 'all' : tag));
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2, mb: 3 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800 }}>{t('traffic.title')}</Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.3 }}>
            {t('traffic.subtitle')}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton onClick={() => setPaused(!paused)} sx={{ color: paused ? '#ffaa00' : '#00d4aa' }} title={paused ? t('traffic.resume') : t('traffic.pause')}>
            {paused ? <PlayArrow /> : <Pause />}
          </IconButton>
          <IconButton onClick={fetchTraffic} sx={{ color: 'primary.main' }} title={t('common.refresh')}>
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      {/* Live indicator */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Box
          sx={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            bgcolor: paused ? '#ffaa00' : '#00d4aa',
            animation: paused ? 'none' : 'pulse 1.5s ease-in-out infinite',
            '@keyframes pulse': {
              '0%, 100%': { opacity: 1 },
              '50%': { opacity: 0.5 },
            },
          }}
        />
        <Typography variant="body2" sx={{ color: 'text.secondary' }}>
          {paused ? t('traffic.paused') : t('traffic.live', { count: data.entries?.length ?? 0 })}
        </Typography>
        <Tooltip
          title={t('traffic.tagHint')}
          placement="bottom"
          arrow
          slotProps={{ tooltip: { sx: { maxWidth: 360, fontSize: '0.8rem' } } }}
        >
          <IconButton size="small" aria-label="Tag info" sx={{ color: 'text.secondary' }}>
            <InfoOutlined fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Error alert */}
      {data.error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {data.error} Ensure vuln-web is running and WEB_SERVER_LOG_PATH is correct in backend/.env
        </Alert>
      )}

      {/* Stat cards */}
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
        {['attack', 'suspicious', 'blocked', 'normal'].map((tag) => (
          <Card
            key={tag}
            onClick={() => toggleTagFilter(tag)}
            sx={{
              flex: 1,
              minWidth: 100,
              cursor: 'pointer',
              border: (theme) => `2px solid ${tagFilter === tag ? TAG_COLORS[tag] : theme.palette.divider}`,
              bgcolor: tagFilter === tag ? `${TAG_COLORS[tag]}15` : 'background.paper',
              '&:hover': { bgcolor: `${TAG_COLORS[tag]}10` },
            }}
          >
            <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
              <Typography variant="h4" sx={{ color: TAG_COLORS[tag], fontWeight: 800 }}>
                {data.summary?.[tag] ?? 0}
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'capitalize' }}>
                {t(`tags.${tag}`)}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Filter bar */}
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2, alignItems: 'center' }}>
        <TextField
          size="small"
          placeholder={t('traffic.searchPlaceholder')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ minWidth: 220 }}
        />
        <ToggleButtonGroup
          value={tagFilter}
          exclusive
          onChange={(_, v) => v != null && setTagFilter(v)}
          size="small"
        >
          <ToggleButton value="all">{t('common.all')}</ToggleButton>
          <ToggleButton value="attack">{t('tags.attack')}</ToggleButton>
          <ToggleButton value="suspicious">{t('tags.suspicious')}</ToggleButton>
          <ToggleButton value="blocked">{t('tags.blocked')}</ToggleButton>
          <ToggleButton value="normal">{t('tags.normal')}</ToggleButton>
        </ToggleButtonGroup>
        <FormControl size="small" sx={{ minWidth: 100 }}>
          <InputLabel>{t('traffic.rows')}</InputLabel>
          <Select value={rowCount} onChange={(e) => setRowCount(Number(e.target.value))} label={t('traffic.rows')}>
            <MenuItem value={50}>50</MenuItem>
            <MenuItem value={100}>100</MenuItem>
            <MenuItem value={200}>200</MenuItem>
            <MenuItem value={500}>500</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 130 }}>
          <InputLabel>{t('traffic.sort')}</InputLabel>
          <Select value={sortDir} onChange={(e) => setSortDir(e.target.value)} label={t('traffic.sort')}>
            <MenuItem value="desc">{t('traffic.newest')}</MenuItem>
            <MenuItem value="asc">{t('traffic.oldest')}</MenuItem>
          </Select>
        </FormControl>
        <FormControlLabel
          control={
            <Checkbox
              checked={hideStatic}
              onChange={(e) => setHideStatic(e.target.checked)}
              size="small"
            />
          }
          label={t('traffic.hideStatic', { defaultValue: 'Hide static assets (CSS/JS)' })}
        />
      </Box>

      {/* Table */}
      <Card>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>{t('traffic.colTime')}</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>{t('traffic.colIp')}</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>{t('traffic.colMethod')}</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>{t('traffic.colPath')}</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>{t('traffic.colQuery')}</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>{t('traffic.colStatus')}</TableCell>
              <TableCell sx={{ fontWeight: 700 }}>{t('traffic.colTag')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.length === 0 && !loading && (
              <TableRow>
                <TableCell colSpan={7} sx={{ py: 4, textAlign: 'center', color: 'text.secondary' }}>
                  {t('traffic.empty')}
                </TableCell>
              </TableRow>
            )}
            {filtered.map((e, i) => (
              <TableRow
                key={i}
                sx={{
                  bgcolor: `${TAG_COLORS[e.tag] || '#333'}08`,
                  borderLeft: `2px solid ${TAG_COLORS[e.tag] || '#333'}`,
                }}
              >
                <TableCell
                  sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary', whiteSpace: 'nowrap' }}
                  title={e.time}
                >
                  {formatLogTime(e.time, language)}
                </TableCell>
                <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{e.ip}</TableCell>
                <TableCell sx={{ color: METHOD_COLORS[e.method] || '#888', fontWeight: 600, fontFamily: 'monospace' }}>
                  {e.method}
                </TableCell>
                <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {e.path}
                </TableCell>
                <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'text.secondary', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {e.query || '—'}
                </TableCell>
                <TableCell sx={{ color: getStatusColor(e.status), fontWeight: 600 }}>{e.status}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    icon={TAG_ICONS[e.tag]}
                    label={t(`tags.${e.tag}`)}
                    sx={{
                      bgcolor: `${TAG_COLORS[e.tag] || '#666'}30`,
                      color: TAG_COLORS[e.tag],
                      fontWeight: 600,
                    }}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </Box>
  );
}
