// IP Management: Blocked IPs (DB) + Rate Limited (JSON/Redis)

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box, Card, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Button, TextField, Dialog,
  DialogTitle, DialogContent, DialogActions, Chip, IconButton, Tooltip,
  CircularProgress, RadioGroup, FormControlLabel, Radio, Select, MenuItem,
  FormControl, InputLabel, useTheme, Tabs, Tab,
} from '@mui/material';
import { Block, Add, Delete, Refresh, Edit, Timer, GppBad } from '@mui/icons-material';
import { toast } from 'react-toastify';
import {
  getBlockedIPs, addBlockedIP, unblockIP, updateBlockedIP,
  getRateLimitedIPs, clearRateLimit, extendRateLimit,
} from '../services/api';
import FilterBar from '../components/shared/FilterBar';
import IPHistoryDrawer from '../components/shared/IPHistoryDrawer';
import useCurrentUser from '../hooks/useCurrentUser';
import { useLanguage } from '../context/LanguageContext';
import { formatLocaleDate } from '../utils/locale';

const BLOCK_HOUR_OPTIONS = [1, 6, 24, 168, 720];
const RATE_EXTEND_SECONDS = [60, 300, 600];
const RATE_MAX_OPTIONS = [5, 10, 15, 20];
const RATE_WINDOW_OPTIONS = [30, 60, 120, 300];

const dialogContentSx = {
  display: 'flex',
  flexDirection: 'column',
  gap: 2.5,
  pt: 3,
  pb: 1,
  overflow: 'visible',
};

const tableHeadCellSx = {
  whiteSpace: 'nowrap',
  fontWeight: 700,
  py: 1.5,
};

function TabPanel({ children, value, index }) {
  if (value !== index) return null;
  return <Box sx={{ pt: 2 }}>{children}</Box>;
}

export default function BlockedIPs() {
  const theme = useTheme();
  const { t, language } = useLanguage();
  const sem = theme.semantic;
  const [tab, setTab] = useState(0);

  const [ips, setIps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingIp, setEditingIp] = useState(null);
  const [form, setForm] = useState({ ip_address: '', reason: '', block_type: 'permanent', hours: 24 });
  const [editForm, setEditForm] = useState({ reason: '', block_type: 'permanent', hours: 24 });

  const [filterValues, setFilterValues] = useState({ block_type: '', repeat_offender: '' });
  const [sortBy, setSortBy] = useState('block_time');
  const [sortDir, setSortDir] = useState('desc');
  const [search, setSearch] = useState('');

  const [rateItems, setRateItems] = useState([]);
  const [rateLoading, setRateLoading] = useState(false);
  const [rateSearch, setRateSearch] = useState('');
  const [rateSortBy, setRateSortBy] = useState('ip_address');
  const [rateSortDir, setRateSortDir] = useState('asc');
  const [extendOpen, setExtendOpen] = useState(false);
  const [extendingIp, setExtendingIp] = useState(null);
  const [extendSeconds, setExtendSeconds] = useState(60);
  const [extendMaxRequests, setExtendMaxRequests] = useState(10);
  const [extendWindow, setExtendWindow] = useState(60);

  const [selectedIP, setSelectedIP] = useState(null);

  const currentUser = useCurrentUser();
  const isAdmin = currentUser?.role === 'admin';

  const SORT_OPTIONS = useMemo(() => [
    { value: 'block_time', label: t('blockedIps.sortBlockTime') },
    { value: 'ip_address', label: t('blockedIps.sortIp') },
    { value: 'incident_count', label: t('blockedIps.sortIncidents') },
  ], [t]);

  const RATE_SORT_OPTIONS = useMemo(() => [
    { value: 'ip_address', label: t('ipManagement.sortIp') },
    { value: 'ttl_seconds', label: t('ipManagement.sortTtl') },
  ], [t]);

  const FILTER_CONFIG = useMemo(() => [
    {
      key: 'block_type',
      label: t('blockedIps.blockType'),
      options: [
        { value: 'permanent', label: t('blockType.permanent') },
        { value: 'temporary', label: t('blockType.temporary') },
      ],
    },
    {
      key: 'repeat_offender',
      label: t('blockedIps.filterRepeatOffender'),
      minWidth: 190,
      options: [
        { value: 'true', label: t('blockedIps.repeatOffender') },
      ],
    },
  ], [t]);

  const fetchIPs = useCallback(async () => {
    setLoading(true);
    try {
      const params = { sort_by: sortBy, sort_dir: sortDir };
      if (filterValues.block_type) params.block_type = filterValues.block_type;
      if (filterValues.repeat_offender) params.repeat_offender = filterValues.repeat_offender;
      if (search) params.search = search;
      const res = await getBlockedIPs(params);
      setIps(res.data);
    } catch {
      toast.error('Failed to load');
    } finally {
      setLoading(false);
    }
  }, [sortBy, sortDir, filterValues, search]);

  const fetchRateLimited = useCallback(async () => {
    setRateLoading(true);
    try {
      const params = { sort_by: rateSortBy, sort_dir: rateSortDir };
      if (rateSearch) params.search = rateSearch;
      const res = await getRateLimitedIPs(params);
      setRateItems(res.data);
    } catch {
      toast.error(t('ipManagement.clearFailed'));
    } finally {
      setRateLoading(false);
    }
  }, [rateSortBy, rateSortDir, rateSearch, t]);

  useEffect(() => {
    if (tab === 0) fetchIPs();
  }, [tab, fetchIPs]);

  useEffect(() => {
    if (tab === 1) fetchRateLimited();
  }, [tab, fetchRateLimited]);

  const handleRefresh = () => {
    if (tab === 0) fetchIPs();
    else fetchRateLimited();
  };

  const handleClearFilters = () => {
    setFilterValues({ block_type: '', repeat_offender: '' });
    setSortBy('block_time');
    setSortDir('desc');
    setSearch('');
  };

  const handleClearRateSearch = () => {
    setRateSearch('');
    setRateSortBy('ip_address');
    setRateSortDir('asc');
  };

  const hasActiveFilters = !!(filterValues.block_type || filterValues.repeat_offender || search);
  const hasActiveRateFilters = !!rateSearch;

  const handleAdd = async () => {
    try {
      const body = {
        ip_address: form.ip_address,
        reason: form.reason,
        block_type: form.block_type,
      };
      if (form.block_type === 'temporary') body.hours = form.hours;
      await addBlockedIP(body);
      toast.success(`IP ${form.ip_address} blocked`);
      setDialogOpen(false);
      setForm({ ip_address: '', reason: '', block_type: 'permanent', hours: 24 });
      fetchIPs();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed to block IP');
    }
  };

  const handleUnblock = async (id, ip) => {
    try {
      await unblockIP(id);
      toast.success(`IP ${ip} unblocked`);
      fetchIPs();
      if (tab === 1) fetchRateLimited();
    } catch { toast.error('Failed to unblock'); }
  };

  const handleClearRate = async (ip) => {
    try {
      await clearRateLimit(ip);
      toast.success(t('ipManagement.clearSuccess', { ip }));
      fetchRateLimited();
    } catch (e) {
      toast.error(e.response?.data?.error || t('ipManagement.clearFailed'));
    }
  };

  const openExtend = (item) => {
    const ttl = item.ttl_seconds || 0;
    const nearestTtl = RATE_EXTEND_SECONDS.reduce((best, s) =>
      (Math.abs(s - ttl) < Math.abs(best - ttl) ? s : best), RATE_EXTEND_SECONDS[0]);
    setExtendingIp(item);
    setExtendSeconds(nearestTtl);
    setExtendMaxRequests(item.max_requests || 10);
    setExtendWindow(item.window_seconds || 60);
    setExtendOpen(true);
  };

  const handleExtend = async () => {
    if (!extendingIp) return;
    try {
      await extendRateLimit(extendingIp.ip_address, {
        seconds: extendSeconds,
        max_requests: extendMaxRequests,
        window_seconds: extendWindow,
      });
      toast.success(t('ipManagement.extendSuccess', { ip: extendingIp.ip_address }));
      setExtendOpen(false);
      setExtendingIp(null);
      fetchRateLimited();
    } catch (e) {
      toast.error(e.response?.data?.error || t('ipManagement.extendFailed'));
    }
  };

  const nearestHourOption = (targetHours) => {
    if (!targetHours || targetHours <= 0) return 24;
    return BLOCK_HOUR_OPTIONS.reduce((best, h) =>
      (Math.abs(h - targetHours) < Math.abs(best - targetHours) ? h : best),
    BLOCK_HOUR_OPTIONS[0]);
  };

  const openEdit = (ip) => {
    let hours = 24;
    if (ip.block_type === 'temporary' && ip.expire_time) {
      const diffMs = new Date(ip.expire_time) - new Date();
      hours = nearestHourOption(Math.ceil(diffMs / 3600000));
    }
    setEditingIp(ip);
    setEditForm({
      reason: ip.reason || '',
      block_type: ip.block_type || 'permanent',
      hours,
    });
    setEditOpen(true);
  };

  const handleEdit = async () => {
    if (!editingIp) return;
    try {
      const body = {
        reason: editForm.reason,
        block_type: editForm.block_type,
      };
      if (editForm.block_type === 'temporary') body.hours = editForm.hours;
      await updateBlockedIP(editingIp.id, body);
      toast.success(t('blockedIps.updateSuccess', { ip: editingIp.ip_address }));
      setEditOpen(false);
      setEditingIp(null);
      fetchIPs();
    } catch (e) {
      toast.error(e.response?.data?.error || t('blockedIps.updateFailed'));
    }
  };

  const formatDate = (iso) => formatLocaleDate(iso, language, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  const formatTtl = (seconds) => {
    if (!seconds || seconds <= 0) {
      return (
        <Tooltip title={t('ipManagement.noTtlHint')}>
          <Chip
            label={t('ipManagement.noTtl')}
            size="small"
            sx={{ bgcolor: sem.chipTemporary.bg, color: sem.chipTemporary.color, fontSize: '0.7rem' }}
          />
        </Tooltip>
      );
    }
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    const label = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
    return (
      <Chip
        label={t('ipManagement.ttlRemaining', { time: label })}
        size="small"
        sx={{ bgcolor: sem.chipTemporary.bg, color: sem.chipTemporary.color, fontSize: '0.7rem' }}
      />
    );
  };

  const formatExpiry = (iso, blockType) => {
    if (blockType === 'permanent') {
      return <Chip label={t('common.never')} size="small" sx={{ bgcolor: sem.chipBlocked.bg, color: sem.chipBlocked.color, fontSize: '0.7rem' }} />;
    }
    if (!iso) return '—';
    const expireDate = new Date(iso);
    const now = new Date();
    const diffMs = expireDate - now;
    if (diffMs <= 0) {
      return <Chip label={t('common.expired')} size="small" sx={{ bgcolor: sem.chipExpired.bg, color: sem.chipExpired.color, fontSize: '0.7rem' }} />;
    }
    const hours = Math.floor(diffMs / 3600000);
    const mins = Math.floor((diffMs % 3600000) / 60000);
    const label = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
    return (
      <Tooltip title={formatDate(iso)}>
        <Chip label={t('common.expiresIn', { time: label })} size="small" sx={{ bgcolor: sem.chipTemporary.bg, color: sem.chipTemporary.color, fontSize: '0.7rem' }} />
      </Tooltip>
    );
  };

  const subtitle = tab === 0
    ? t('ipManagement.subtitleBlocked', { count: ips.length })
    : t('ipManagement.subtitleRateLimited', { count: rateItems.length });

  const ipButtonSx = {
    fontFamily: 'monospace', fontSize: '0.9rem', fontWeight: 700,
    color: '#ff6d00', p: 0, minWidth: 'unset',
    textTransform: 'none',
    '&:hover': { color: '#ffaa00', bgcolor: 'transparent', textDecoration: 'underline' },
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>{t('ipManagement.title')}</Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>{subtitle}</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {isAdmin && tab === 0 && (
            <Button
              variant="outlined"
              startIcon={<Add />}
              onClick={() => setDialogOpen(true)}
              color="error"
            >
              {t('blockedIps.blockIp')}
            </Button>
          )}
          <IconButton onClick={handleRefresh} sx={{ color: 'primary.main' }}><Refresh /></IconButton>
        </Box>
      </Box>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ borderBottom: 1, borderColor: 'divider', mb: 0 }}
      >
        <Tab icon={<Block sx={{ fontSize: 18 }} />} iconPosition="start" label={t('ipManagement.tabBlocked')} />
        <Tab icon={<Timer sx={{ fontSize: 18 }} />} iconPosition="start" label={t('ipManagement.tabRateLimited')} />
      </Tabs>

      <TabPanel value={tab} index={0}>
        <FilterBar
          filters={FILTER_CONFIG}
          values={filterValues}
          onChange={(key, val) => setFilterValues(prev => ({ ...prev, [key]: val }))}
          sortOptions={SORT_OPTIONS}
          sortBy={sortBy}
          sortDir={sortDir}
          onSortBy={setSortBy}
          onSortDir={setSortDir}
          searchValue={search}
          searchPlaceholder={t('blockedIps.searchPlaceholder')}
          onSearch={setSearch}
          hasActiveFilters={hasActiveFilters}
          onClear={handleClearFilters}
        />

        <Card>
          <TableContainer>
            <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={tableHeadCellSx}>{t('blockedIps.colIp')}</TableCell>
                <TableCell sx={tableHeadCellSx}>{t('blockedIps.colReason')}</TableCell>
                <TableCell sx={tableHeadCellSx}>{t('blockedIps.colType')}</TableCell>
                <TableCell sx={tableHeadCellSx}>{t('blockedIps.colBlockedAt')}</TableCell>
                <TableCell sx={tableHeadCellSx}>{t('blockedIps.colExpires')}</TableCell>
                <TableCell sx={tableHeadCellSx}>{t('blockedIps.colIncidents')}</TableCell>
                {isAdmin && <TableCell align="center" sx={tableHeadCellSx}>{t('common.actions')}</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                  <TableRow><TableCell colSpan={isAdmin ? 7 : 6} align="center" sx={{ py: 6 }}><CircularProgress size={28} /></TableCell></TableRow>
                ) : ips.length === 0 ? (
                  <TableRow><TableCell colSpan={isAdmin ? 7 : 6} align="center" sx={{ py: 6, color: 'text.secondary' }}>{t('blockedIps.empty')}</TableCell></TableRow>
                ) : ips.map(ip => (
                  <TableRow key={ip.id} hover>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Button variant="text" size="small" onClick={() => setSelectedIP(ip.ip_address)} sx={ipButtonSx}>
                          {ip.ip_address}
                        </Button>
                        {ip.is_repeat_offender && (
                          <Tooltip title={t('blockedIps.repeatOffenderTooltip', { threshold: ip.incident_count })}>
                            <Chip
                              icon={<GppBad sx={{ fontSize: 14 }} />}
                              label={t('blockedIps.repeatOffender')}
                              size="small"
                              sx={{
                                height: 20,
                                fontSize: '0.65rem',
                                fontWeight: 700,
                                bgcolor: 'rgba(255,23,68,0.15)',
                                color: '#ff1744',
                                border: '1px solid rgba(255,23,68,0.3)',
                                '& .MuiChip-icon': { color: '#ff1744' },
                              }}
                            />
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.85rem', color: 'text.secondary' }}>{ip.reason}</TableCell>
                    <TableCell>
                      <Chip label={t(`blockType.${ip.block_type}`)} size="small"
                        sx={ip.block_type === 'permanent'
                          ? { color: sem.chipBlocked.color, bgcolor: sem.chipBlocked.bg }
                          : { color: sem.chipTemporary.color, bgcolor: sem.chipTemporary.bg }} />
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>{formatDate(ip.block_time)}</TableCell>
                    <TableCell sx={{ fontSize: '0.8rem', color: 'text.secondary', whiteSpace: 'nowrap' }}>{formatExpiry(ip.expire_time, ip.block_type)}</TableCell>
                    <TableCell>
                      <Chip label={ip.incident_count} size="small" sx={{ bgcolor: sem.chipIncident.bg, color: sem.chipIncident.color }} />
                    </TableCell>
                    {isAdmin && (
                      <TableCell align="center" sx={{ whiteSpace: 'nowrap' }}>
                        <Tooltip title={t('blockedIps.edit')}>
                          <IconButton size="small" onClick={() => openEdit(ip)} sx={{ color: 'primary.main', mr: 0.5 }}>
                            <Edit sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={t('blockedIps.unblock')}>
                          <IconButton size="small" onClick={() => handleUnblock(ip.id, ip.ip_address)} sx={{ color: '#ff4444' }}>
                            <Delete sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      </TabPanel>

      <TabPanel value={tab} index={1}>
        <FilterBar
          filters={[]}
          values={{}}
          onChange={() => {}}
          sortOptions={RATE_SORT_OPTIONS}
          sortBy={rateSortBy}
          sortDir={rateSortDir}
          onSortBy={setRateSortBy}
          onSortDir={setRateSortDir}
          searchValue={rateSearch}
          searchPlaceholder={t('ipManagement.searchRatePlaceholder')}
          onSearch={setRateSearch}
          hasActiveFilters={hasActiveRateFilters}
          onClear={handleClearRateSearch}
        />

        <Card>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell sx={tableHeadCellSx}>{t('ipManagement.colIp')}</TableCell>
                  <TableCell sx={{ ...tableHeadCellSx, minWidth: 140 }}>{t('ipManagement.colListedAt')}</TableCell>
                  <TableCell sx={tableHeadCellSx}>{t('ipManagement.colWindow')}</TableCell>
                  <TableCell sx={tableHeadCellSx}>{t('ipManagement.colMaxReq')}</TableCell>
                  <TableCell sx={tableHeadCellSx}>{t('ipManagement.colExpires')}</TableCell>
                  {isAdmin && <TableCell align="center" sx={tableHeadCellSx}>{t('common.actions')}</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {rateLoading ? (
                  <TableRow><TableCell colSpan={isAdmin ? 6 : 5} align="center" sx={{ py: 6 }}><CircularProgress size={28} /></TableCell></TableRow>
                ) : rateItems.length === 0 ? (
                  <TableRow><TableCell colSpan={isAdmin ? 6 : 5} align="center" sx={{ py: 6, color: 'text.secondary' }}>{t('ipManagement.emptyRate')}</TableCell></TableRow>
                ) : rateItems.map((item) => (
                  <TableRow key={item.ip_address} hover>
                    <TableCell>
                      <Button variant="text" size="small" onClick={() => setSelectedIP(item.ip_address)} sx={ipButtonSx}>
                        {item.ip_address}
                      </Button>
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.8rem' }}>
                      {item.listed_at ? formatDate(item.listed_at) : '—'}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.85rem' }}>
                      {t('ipManagement.windowValue', { seconds: item.window_seconds })}
                    </TableCell>
                    <TableCell sx={{ fontSize: '0.85rem' }}>
                      {t('ipManagement.maxReqValue', { count: item.max_requests })}
                    </TableCell>
                    <TableCell>{formatTtl(item.ttl_seconds)}</TableCell>
                    {isAdmin && (
                      <TableCell align="center">
                        <Tooltip title={t('ipManagement.extendRate')}>
                          <IconButton size="small" onClick={() => openExtend(item)} sx={{ color: 'primary.main', mr: 0.5 }}>
                            <Edit sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={t('ipManagement.clearRate')}>
                          <IconButton size="small" onClick={() => handleClearRate(item.ip_address)} sx={{ color: '#ff4444' }}>
                            <Delete sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      </TabPanel>

      {isAdmin && (
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle sx={{ pb: 1 }}>{t('blockedIps.dialogTitle')}</DialogTitle>
          <DialogContent sx={dialogContentSx}>
            <TextField
              fullWidth
              margin="normal"
              label={t('blockedIps.ipLabel')}
              value={form.ip_address}
              onChange={e => setForm(f => ({ ...f, ip_address: e.target.value }))}
              placeholder="e.g. 192.168.1.100"
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              fullWidth
              margin="normal"
              label={t('blockedIps.reason')}
              value={form.reason}
              onChange={e => setForm(f => ({ ...f, reason: e.target.value }))}
              InputLabelProps={{ shrink: true }}
            />
            <RadioGroup value={form.block_type} onChange={e => setForm(f => ({ ...f, block_type: e.target.value }))}>
              <FormControlLabel value="permanent" control={<Radio />} label={t('blockType.permanent')} />
              <FormControlLabel value="temporary" control={<Radio />} label={t('blockType.temporary')} />
            </RadioGroup>
            {form.block_type === 'temporary' && (
              <FormControl fullWidth size="small">
                <InputLabel id="block-hours-label" shrink>{t('blockedIps.duration')}</InputLabel>
                <Select
                  labelId="block-hours-label"
                  value={form.hours}
                  label={t('blockedIps.duration')}
                  onChange={e => setForm(f => ({ ...f, hours: e.target.value }))}
                >
                  {BLOCK_HOUR_OPTIONS.map(h => (
                    <MenuItem key={h} value={h}>{h >= 720 ? `${h} (30 days)` : h === 168 ? '168 (7 days)' : `${h} hour${h > 1 ? 's' : ''}`}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>{t('common.cancel')}</Button>
            <Button variant="contained" onClick={handleAdd} color="error" disabled={!form.ip_address}>{t('blockedIps.blockIp')}</Button>
          </DialogActions>
        </Dialog>
      )}

      {isAdmin && (
        <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle sx={{ pb: 1 }}>{t('blockedIps.editTitle')}</DialogTitle>
          <DialogContent sx={dialogContentSx}>
            <Box>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                {t('blockedIps.ipLabel')}
              </Typography>
              <Typography
                component="code"
                sx={{ fontFamily: 'monospace', fontSize: '1rem', fontWeight: 700, color: '#ff6d00' }}
              >
                {editingIp?.ip_address || '—'}
              </Typography>
            </Box>
            <TextField
              fullWidth
              margin="normal"
              label={t('blockedIps.reason')}
              value={editForm.reason}
              onChange={(e) => setEditForm((f) => ({ ...f, reason: e.target.value }))}
              InputLabelProps={{ shrink: true }}
            />
            <RadioGroup value={editForm.block_type} onChange={(e) => setEditForm((f) => ({ ...f, block_type: e.target.value }))}>
              <FormControlLabel value="permanent" control={<Radio />} label={t('blockType.permanent')} />
              <FormControlLabel value="temporary" control={<Radio />} label={t('blockType.temporary')} />
            </RadioGroup>
            {editForm.block_type === 'temporary' && (
              <FormControl fullWidth size="small">
                <InputLabel id="edit-hours-label" shrink>{t('blockedIps.duration')}</InputLabel>
                <Select
                  labelId="edit-hours-label"
                  value={editForm.hours}
                  label={t('blockedIps.duration')}
                  onChange={(e) => setEditForm((f) => ({ ...f, hours: e.target.value }))}
                >
                  {BLOCK_HOUR_OPTIONS.map((h) => (
                    <MenuItem key={h} value={h}>{h >= 720 ? `${h} (30 days)` : h === 168 ? '168 (7 days)' : `${h} hour${h > 1 ? 's' : ''}`}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.5 }}>{t('blockedIps.editHint')}</Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEditOpen(false)}>{t('common.cancel')}</Button>
            <Button variant="contained" onClick={handleEdit} color="primary">{t('common.save')}</Button>
          </DialogActions>
        </Dialog>
      )}

      {isAdmin && (
        <Dialog open={extendOpen} onClose={() => setExtendOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle sx={{ pb: 1 }}>{t('ipManagement.extendTitle')}</DialogTitle>
          <DialogContent sx={dialogContentSx}>
            <Box>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 0.5 }}>
                {t('ipManagement.ipReadonly')}
              </Typography>
              <Typography
                component="code"
                sx={{ fontFamily: 'monospace', fontSize: '1rem', fontWeight: 700, color: '#ff6d00' }}
              >
                {extendingIp?.ip_address || '—'}
              </Typography>
            </Box>
            <FormControl fullWidth size="small">
              <InputLabel id="extend-ttl-label" shrink>{t('ipManagement.extendDuration')}</InputLabel>
              <Select
                labelId="extend-ttl-label"
                value={extendSeconds}
                label={t('ipManagement.extendDuration')}
                onChange={(e) => setExtendSeconds(e.target.value)}
              >
                {RATE_EXTEND_SECONDS.map((s) => (
                  <MenuItem key={s} value={s}>{s}s</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth size="small">
              <InputLabel id="extend-max-label" shrink>{t('ipManagement.extendMaxReq')}</InputLabel>
              <Select
                labelId="extend-max-label"
                value={extendMaxRequests}
                label={t('ipManagement.extendMaxReq')}
                onChange={(e) => setExtendMaxRequests(e.target.value)}
              >
                {RATE_MAX_OPTIONS.map((n) => (
                  <MenuItem key={n} value={n}>{n}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth size="small">
              <InputLabel id="extend-window-label" shrink>{t('ipManagement.extendWindow')}</InputLabel>
              <Select
                labelId="extend-window-label"
                value={extendWindow}
                label={t('ipManagement.extendWindow')}
                onChange={(e) => setExtendWindow(e.target.value)}
              >
                {RATE_WINDOW_OPTIONS.map((s) => (
                  <MenuItem key={s} value={s}>{s}s</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.5 }}>
              {t('ipManagement.extendHint')}
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setExtendOpen(false)}>{t('common.cancel')}</Button>
            <Button variant="contained" onClick={handleExtend} color="primary">{t('common.save')}</Button>
          </DialogActions>
        </Dialog>
      )}

      <IPHistoryDrawer
        ip={selectedIP}
        onClose={() => setSelectedIP(null)}
        isAdmin={isAdmin}
      />
    </Box>
  );
}
