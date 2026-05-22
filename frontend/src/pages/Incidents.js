import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Box, Card, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TablePagination, Button, IconButton,
  Tooltip, CircularProgress, Select, MenuItem, FormControl,
  Dialog, DialogTitle, DialogContent, DialogActions, Checkbox,
} from '@mui/material';
import {
  Refresh, OpenInNew, Download, PlayArrow,
  Lock, AccessTime, Visibility, CheckCircle, Cancel, Checklist,
} from '@mui/icons-material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  getIncidents, exportIncidentsCsv, simulateAttack, updateIncidentStatus, bulkUpdateIncidentStatus,
} from '../services/api';
import { SeverityChip, StatusChip, AttackTypeChip } from '../components/shared/Chips';
import SimulateDialog from '../components/incidents/SimulateDialog';
import FilterBar from '../components/shared/FilterBar';
import DateRangeFilter, { useDatePresetOptions } from '../components/shared/DateRangeFilter';
import { useLanguage } from '../context/LanguageContext';
import { formatLocaleDate } from '../utils/locale';
import IPHistoryDrawer from '../components/shared/IPHistoryDrawer';
import useCurrentUser from '../hooks/useCurrentUser';
import { getFlagEmoji } from '../utils/country';
import { iconSize } from '../theme';

const ATTACK_TYPES = ['SQL_INJECTION', 'XSS', 'BRUTE_FORCE', 'PATH_TRAVERSAL', 'COMMAND_INJECTION', 'SCANNER', 'LFI_RFI', 'FILE_UPLOAD'];

const STATUS_OPTIONS_ALL = ['new', 'investigating', 'resolved', 'false_positive'];

/** Ongoing = work queue only (new + investigating). Resolved/archive → All Incidents. */
function buildStatusQuery(mode, statusFilter) {
  if (mode === 'all') {
    return statusFilter ? { status: statusFilter } : {};
  }
  if (statusFilter === 'new' || statusFilter === 'investigating') {
    return { status: statusFilter };
  }
  return { status_in: 'new,investigating' };
}

export default function Incidents({ mode = 'ongoing' }) {
  const isAllMode = mode === 'all';
  const { t, language } = useLanguage();
  const datePresetOptions = useDatePresetOptions();
  const [incidents, setIncidents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(20);
  const [loading, setLoading] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(() => searchParams.get('search') || '');
  const [severity, setSeverity] = useState('');
  const [status, setStatus] = useState('');
  const [attackType, setAttackType] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');
  const [datePreset, setDatePreset] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [simulateOpen, setSimulateOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportPreset, setExportPreset] = useState('all');
  const [exportFrom, setExportFrom] = useState('');
  const [exportTo, setExportTo] = useState('');
  const [exporting, setExporting] = useState(false);
  const [selectedIP, setSelectedIP] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [selectionMode, setSelectionMode] = useState(false);

  const navigate = useNavigate();
  const syncSearchParam = useCallback((value) => {
    const next = new URLSearchParams(searchParams);
    const trimmed = (value || '').trim();
    if (trimmed) next.set('search', trimmed);
    else next.delete('search');
    setSearchParams(next, { replace: true });
  }, [searchParams, setSearchParams]);

  const applySearch = useCallback((value) => {
    setSearch(value);
    setPage(0);
    syncSearchParam(value);
  }, [syncSearchParam]);

  const currentUser = useCurrentUser();
  const isAdmin = currentUser?.role === 'admin';
  const canExport = ['admin', 'analyst'].includes(currentUser?.role);

  const fetchSeqRef = useRef(0);

  const fetchIncidents = useCallback(async (overrides = {}) => {
    const seq = ++fetchSeqRef.current;
    setLoading(true);
    try {
      const effFrom = overrides.date_from !== undefined ? overrides.date_from : dateFrom;
      const effTo = overrides.date_to !== undefined ? overrides.date_to : dateTo;
      const params = {
        page: page + 1, per_page: perPage,
        search, severity, attack_type: attackType,
        sort_by: sortBy, sort_dir: sortDir,
        ...buildStatusQuery(mode, status),
      };
      if (effFrom) params.date_from = effFrom;
      if (effTo) params.date_to = effTo;
      const res = await getIncidents(params);
      if (seq !== fetchSeqRef.current) return;
      setIncidents(res.data.incidents);
      setTotal(res.data.total);
    } catch {
      if (seq === fetchSeqRef.current) toast.error('Failed to load incidents');
    } finally {
      if (seq === fetchSeqRef.current) setLoading(false);
    }
  }, [page, perPage, search, severity, status, attackType, sortBy, sortDir, dateFrom, dateTo, mode]);

  const handleDateRangeApply = useCallback((from, to) => {
    setDateFrom(from || '');
    setDateTo(to || '');
    setPage(0);
    fetchIncidents({ date_from: from || '', date_to: to || '' });
  }, [fetchIncidents]);

  const exitSelectionMode = useCallback(() => {
    setSelectionMode(false);
    setSelectedIds([]);
  }, []);

  const showBulkUi = isAdmin && selectionMode;
  const tableColSpan = showBulkUi ? 10 : 9;

  useEffect(() => { fetchIncidents(); }, [fetchIncidents]);

  useEffect(() => {
    const q = searchParams.get('search') || '';
    setSearch((prev) => {
      if (prev !== q) {
        setPage(0);
        return q;
      }
      return prev;
    });
  }, [searchParams]);

  useEffect(() => {
    setStatus('');
    setPage(0);
    exitSelectionMode();
  }, [mode, exitSelectionMode]);

  const handleClearFilters = () => {
    setSeverity(''); setStatus(''); setAttackType('');
    applySearch('');
    setDatePreset('all');
    setSortBy('created_at'); setSortDir('desc');
    setPage(0);
    exitSelectionMode();
    handleDateRangeApply('', '');
  };

  const formatDateShort = useCallback((iso) => formatLocaleDate(iso, language, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  }), [language]);

  const hasActiveFilters = !!(severity || status || attackType || search || dateFrom || dateTo);

  const activeChips = useMemo(() => {
    const chips = [];
    if (search) chips.push({ key: 'search', label: `Search: ${search}`, onDelete: () => applySearch('') });
    if (severity) chips.push({ key: 'severity', label: `Severity: ${severity}`, onDelete: () => { setSeverity(''); setPage(0); } });
    if (status) {
      chips.push({
        key: 'status',
        label: `${t('incidents.status')}: ${t(`status.${status}`)}`,
        onDelete: () => { setStatus(''); setPage(0); },
      });
    }
    if (attackType) chips.push({ key: 'attack', label: `Type: ${attackType}`, onDelete: () => { setAttackType(''); setPage(0); } });
    if (dateFrom || dateTo) {
      const presetLabel = datePresetOptions.find((p) => p.value === datePreset)?.label || t('dateRange.custom');
      const rangeHint = dateFrom && dateTo
        ? `${formatDateShort(dateFrom)} – ${formatDateShort(dateTo)}`
        : presetLabel;
      chips.push({
        key: 'date',
        label: `${t('dateRange.label')}: ${rangeHint}`,
        onDelete: () => {
          setDatePreset('all');
          handleDateRangeApply('', '');
        },
      });
    }
    return chips;
  }, [search, severity, status, attackType, dateFrom, dateTo, datePreset, datePresetOptions, t, handleDateRangeApply, formatDateShort]);

  const SORT_OPTIONS = useMemo(() => [
    { value: 'created_at', label: t('incidents.sortCreated') },
    { value: 'severity', label: t('incidents.sortSeverity') },
    { value: 'status', label: t('incidents.sortStatus') },
    { value: 'source_ip', label: t('incidents.sortIp') },
    { value: 'attack_type', label: t('incidents.sortAttack') },
  ], [t]);

  const FILTER_CONFIG = useMemo(() => [
    {
      key: 'severity',
      label: t('incidents.severity'),
      options: ['critical', 'high', 'medium', 'low'].map((s) => ({ value: s, label: t(`severity.${s}`) })),
    },
    {
      key: 'status',
      label: t('incidents.status'),
      options: isAllMode
        ? STATUS_OPTIONS_ALL.map((s) => ({ value: s, label: t(`status.${s}`) }))
        : [
          { value: 'new', label: t('status.new') },
          { value: 'investigating', label: t('status.investigating') },
        ],
    },
    {
      key: 'attackType',
      label: t('incidents.attackType'),
      options: ATTACK_TYPES.map((type) => ({ value: type, label: type.replace(/_/g, ' ') })),
    },
  ], [t, isAllMode]);

  const pageIds = useMemo(() => incidents.map((i) => i.id), [incidents]);
  const allPageSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.includes(id));
  const somePageSelected = pageIds.some((id) => selectedIds.includes(id));

  const toggleSelectAll = () => {
    if (allPageSelected) {
      setSelectedIds((prev) => prev.filter((id) => !pageIds.includes(id)));
    } else {
      setSelectedIds((prev) => [...new Set([...prev, ...pageIds])]);
    }
  };

  const toggleSelectOne = (id) => {
    setSelectedIds((prev) => (
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    ));
  };

  const handleBulkStatus = async (newStatus) => {
    if (!selectedIds.length) return;
    setBulkLoading(true);
    try {
      const res = await bulkUpdateIncidentStatus(selectedIds, newStatus);
      const count = res.data.updated?.length ?? selectedIds.length;
      toast.success(t('incidents.bulkSuccess', { count }));
      exitSelectionMode();
      fetchIncidents();
    } catch (err) {
      const msg = err.response?.data?.error || t('incidents.bulkFailed');
      toast.error(msg);
    } finally {
      setBulkLoading(false);
    }
  };

  const handleStatusChange = async (e, incidentId, newStatus) => {
    e.stopPropagation();
    try {
      await updateIncidentStatus(incidentId, newStatus);
      toast.success('Status updated');
      fetchIncidents();
    } catch {
      toast.error('Failed to update status');
    }
  };

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      const params = { list_scope: isAllMode ? 'all' : 'ongoing' };
      if (severity) params.severity = severity;
      if (attackType) params.attack_type = attackType;
      Object.assign(params, buildStatusQuery(mode, status));
      if (search) params.search = search;
      if (exportFrom) params.date_from = exportFrom;
      if (exportTo) params.date_to = exportTo;
      const res = await exportIncidentsCsv(params);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = isAllMode ? 'incidents-all.csv' : 'incidents-ongoing.csv';
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('CSV exported');
      setExportOpen(false);
    } catch {
      toast.error('Export failed');
    } finally {
      setExporting(false);
    }
  };

  const handleSimulate = async (data) => {
    try {
      await simulateAttack(data);
      toast.success('Attack simulated! Incident created.');
      setSimulateOpen(false);
      fetchIncidents();
    } catch {
      toast.error('Simulation failed');
    }
  };

  const handleInjectSuccess = useCallback((incidentIds = []) => {
    fetchIncidents();
    if (incidentIds.length === 0) {
      const delays = [2000, 5000];
      delays.forEach((ms) => {
        setTimeout(() => fetchIncidents(), ms);
      });
    }
  }, [fetchIncidents]);

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            {isAllMode ? t('incidents.titleAll') : t('incidents.titleOngoing')}
          </Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.25 }}>
            {isAllMode
              ? t('incidents.subtitleAll', { count: total })
              : t('incidents.subtitleOngoing', { count: total })}
          </Typography>
          {!isAllMode && (
            <Typography variant="caption" sx={{ color: 'text.disabled', display: 'block', mt: 0.5 }}>
              {t('incidents.ongoingHint')}
            </Typography>
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {isAdmin && (
            <Button
              variant={selectionMode ? 'contained' : 'outlined'}
              color={selectionMode ? 'inherit' : 'primary'}
              size="small"
              startIcon={<Checklist sx={{ fontSize: 18 }} />}
              onClick={() => {
                if (selectionMode) exitSelectionMode();
                else setSelectionMode(true);
              }}
              sx={{ alignSelf: 'center' }}
            >
              {selectionMode ? t('incidents.cancelSelect') : t('incidents.selectMode')}
            </Button>
          )}
          <Button
            variant="outlined"
            startIcon={<PlayArrow sx={{ fontSize: 20 }} />}
            onClick={() => setSimulateOpen(true)}
            color="secondary"
          >
            {t('incidents.simulate')}
          </Button>
          {canExport && (
            <Button
              variant="outlined"
              startIcon={<Download sx={{ fontSize: 20 }} />}
              onClick={() => {
                setExportPreset(datePreset);
                setExportFrom(dateFrom);
                setExportTo(dateTo);
                setExportOpen(true);
              }}
              color="primary"
            >
              {t('incidents.exportCsv')}
            </Button>
          )}
          <IconButton onClick={fetchIncidents} color="primary" size="small">
            <Refresh sx={{ fontSize: iconSize.action }} />
          </IconButton>
        </Box>
      </Box>

      <FilterBar
        filters={FILTER_CONFIG}
        values={{ severity, status, attackType }}
        onChange={(key, val) => {
          if (key === 'severity') { setSeverity(val); setPage(0); }
          if (key === 'status') { setStatus(val); setPage(0); }
          if (key === 'attackType') { setAttackType(val); setPage(0); }
        }}
        sortOptions={SORT_OPTIONS}
        sortBy={sortBy}
        sortDir={sortDir}
        onSortBy={(val) => { setSortBy(val); setPage(0); }}
        onSortDir={(val) => { setSortDir(val); setPage(0); }}
        searchValue={search}
        searchPlaceholder={t('incidents.searchPlaceholder')}
        onSearch={applySearch}
        hasActiveFilters={hasActiveFilters}
        onClear={handleClearFilters}
        activeChips={activeChips}
        extra={(
          <DateRangeFilter
            preset={datePreset}
            dateFrom={dateFrom}
            dateTo={dateTo}
            onPresetChange={setDatePreset}
            onApply={handleDateRangeApply}
          />
        )}
      />

      {showBulkUi && selectedIds.length > 0 && (
        <Box
          sx={{
            display: 'flex', alignItems: 'center', gap: 1, mb: 2, p: 1.5,
            borderRadius: 2, bgcolor: 'action.selected', flexWrap: 'wrap',
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 600, mr: 1 }}>
            {t('incidents.selected', { count: selectedIds.length })}
          </Typography>
          <Button
            size="small"
            variant="contained"
            color="success"
            startIcon={<CheckCircle sx={{ fontSize: 18 }} />}
            disabled={bulkLoading}
            onClick={() => handleBulkStatus('resolved')}
          >
            {t('incidents.markResolved')}
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="warning"
            startIcon={<Cancel sx={{ fontSize: 18 }} />}
            disabled={bulkLoading}
            onClick={() => handleBulkStatus('false_positive')}
          >
            {t('incidents.markFalsePositive')}
          </Button>
          <Button size="small" onClick={() => setSelectedIds([])} disabled={bulkLoading}>
            {t('incidents.clearSelection')}
          </Button>
          <Button size="small" onClick={exitSelectionMode} disabled={bulkLoading} sx={{ ml: 'auto' }}>
            {t('incidents.cancelSelect')}
          </Button>
        </Box>
      )}

      <Card>
        <TableContainer sx={{ maxHeight: 'calc(100vh - 320px)' }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                {showBulkUi && (
                  <TableCell padding="checkbox">
                    <Checkbox
                      size="small"
                      checked={allPageSelected}
                      indeterminate={somePageSelected && !allPageSelected}
                      onChange={toggleSelectAll}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </TableCell>
                )}
                <TableCell>
                  <Tooltip title={t('incidents.idTooltip')}>
                    <span>{t('incidents.colId')}</span>
                  </Tooltip>
                </TableCell>
                <TableCell>{t('incidents.colDetected')}</TableCell>
                <TableCell>{t('incidents.colSourceIp')}</TableCell>
                <TableCell>{t('incidents.colAttackType')}</TableCell>
                <TableCell>{t('incidents.colSeverity')}</TableCell>
                <TableCell>{t('incidents.colStatus')}</TableCell>
                <TableCell>{t('incidents.colPath')}</TableCell>
                <TableCell>
                  <Tooltip title={t('incidents.responseTip')}>
                    <span>{t('incidents.colResponse')}</span>
                  </Tooltip>
                </TableCell>
                <TableCell align="center">{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={tableColSpan} align="center" sx={{ py: 6 }}>
                    <CircularProgress size={32} />
                  </TableCell>
                </TableRow>
              ) : incidents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={tableColSpan} align="center" sx={{ py: 6, color: 'text.secondary' }}>
                    {t('incidents.empty')}
                  </TableCell>
                </TableRow>
              ) : incidents.map((incident) => (
                <TableRow
                  key={incident.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => {
                    if (showBulkUi) toggleSelectOne(incident.id);
                    else navigate(`/incidents/${incident.id}`);
                  }}
                >
                  {showBulkUi && (
                    <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        size="small"
                        checked={selectedIds.includes(incident.id)}
                        onChange={() => toggleSelectOne(incident.id)}
                      />
                    </TableCell>
                  )}
                  <TableCell sx={{ color: 'text.secondary', fontSize: '0.8rem' }}>{incident.id}</TableCell>
                  <TableCell sx={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>{formatDateShort(incident.created_at)}</TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="text"
                      size="small"
                      onClick={() => setSelectedIP(incident.source_ip)}
                      sx={{
                        fontFamily: 'monospace', fontSize: '0.85rem', color: 'warning.main',
                        p: 0, minWidth: 'unset', textTransform: 'none',
                      }}
                    >
                      {incident.country_code && (
                        <span style={{ marginRight: 4 }} title={incident.country_code}>
                          {getFlagEmoji(incident.country_code)}
                        </span>
                      )}
                      {incident.source_ip}
                    </Button>
                  </TableCell>
                  <TableCell><AttackTypeChip type={incident.attack_type} /></TableCell>
                  <TableCell><SeverityChip severity={incident.severity} /></TableCell>
                  <TableCell><StatusChip status={incident.status} /></TableCell>
                  <TableCell sx={{ maxWidth: 200 }}>
                    <Typography noWrap sx={{ fontSize: '0.8rem', color: 'text.secondary', fontFamily: 'monospace' }}>
                      {incident.request_path || '—'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {incident.severity === 'critical' || incident.severity === 'high' ? (
                      <Tooltip title={incident.severity === 'critical' ? t('incidents.blockedPerm') : t('incidents.blockedTemp')}>
                        <Lock sx={{ fontSize: iconSize.inline, color: 'error.main' }} />
                      </Tooltip>
                    ) : incident.severity === 'medium' ? (
                      <Tooltip title={t('incidents.rateLimited')}>
                        <AccessTime sx={{ fontSize: iconSize.inline, color: 'warning.main' }} />
                      </Tooltip>
                    ) : (
                      <Tooltip title={t('incidents.monitored')}>
                        <Visibility sx={{ fontSize: iconSize.inline, color: 'text.secondary' }} />
                      </Tooltip>
                    )}
                  </TableCell>
                  <TableCell align="center" onClick={(e) => e.stopPropagation()}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                      <FormControl size="small" sx={{ minWidth: 120 }}>
                        <Select
                          value={incident.status}
                          onChange={(e) => handleStatusChange(e, incident.id, e.target.value)}
                          displayEmpty
                          sx={{ fontSize: '0.75rem', height: 32 }}
                        >
                          {STATUS_OPTIONS_ALL.map((s) => (
                            <MenuItem key={s} value={s} sx={{ fontSize: '0.8rem' }}>
                              {t(`status.${s}`)}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      <Tooltip title={t('incidents.viewDetails')}>
                        <IconButton size="small" onClick={() => navigate(`/incidents/${incident.id}`)}>
                          <OpenInNew sx={{ fontSize: iconSize.inline }} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          count={total}
          page={page}
          rowsPerPage={perPage}
          onPageChange={(e, p) => setPage(p)}
          onRowsPerPageChange={(e) => { setPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          rowsPerPageOptions={[10, 20, 50]}
          labelRowsPerPage={t('common.rowsPerPage')}
        />
      </Card>

      <SimulateDialog
        open={simulateOpen}
        onClose={() => setSimulateOpen(false)}
        onSimulate={handleSimulate}
        onInjectSuccess={handleInjectSuccess}
      />

      <Dialog open={exportOpen} onClose={() => setExportOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{t('incidents.exportTitle')}</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <Typography variant="body2" sx={{ color: 'text.secondary', mb: 2 }}>
            {isAllMode ? t('incidents.exportHintAll') : t('incidents.exportHintOngoing')}
          </Typography>
          <DateRangeFilter
            preset={exportPreset}
            dateFrom={exportFrom}
            dateTo={exportTo}
            onPresetChange={setExportPreset}
            onDateFromChange={setExportFrom}
            onDateToChange={setExportTo}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExportOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" color="primary" onClick={handleExportCsv} disabled={exporting}>
            {exporting ? t('incidents.exporting') : t('incidents.downloadCsv')}
          </Button>
        </DialogActions>
      </Dialog>

      <IPHistoryDrawer ip={selectedIP} onClose={() => setSelectedIP(null)} isAdmin={isAdmin} />
    </Box>
  );
}
