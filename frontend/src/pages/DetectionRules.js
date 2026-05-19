// frontend/src/pages/DetectionRules.js
// REVISI 1B: tambah FilterBar (Status, Attack Type, Sort)
// REVISI 3B: sembunyikan Add/Edit/Delete jika bukan admin

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box, Card, CardContent, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Button, TextField, Dialog,
  DialogTitle, DialogContent, DialogActions, Switch, Chip, IconButton,
  Tooltip, CircularProgress, Select, MenuItem, FormControl, InputLabel,
  Tabs, Tab,
} from '@mui/material';
import { Add, Delete, Edit, Refresh, Science } from '@mui/icons-material';
import { toast } from 'react-toastify';
import { getRules, createRule, updateRule, deleteRule, testPayload } from '../services/api';
import FilterBar from '../components/shared/FilterBar';
import useCurrentUser from '../hooks/useCurrentUser';
import { useLanguage } from '../context/LanguageContext';

const ATTACK_TYPES = ['SQL_INJECTION', 'XSS', 'BRUTE_FORCE', 'PATH_TRAVERSAL', 'COMMAND_INJECTION', 'SCANNER', 'LFI_RFI'];

const DEFAULT_PAYLOAD = "' OR 1=1--";
const EXAMPLE_LOG_LINE = '192.168.1.50 - - [15/May/2026:10:30:00 +0000] "GET /search?q=\'+OR+1=1+UNION+SELECT+username,password+FROM+users-- HTTP/1.1" 200 512 "-" "sqlmap/1.7"';

export function DetectionRules() {
  const { t } = useLanguage();
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editRule, setEditRule] = useState(null);
  const [form, setForm] = useState({ rule_name: '', attack_type: 'SQL_INJECTION', pattern: '', severity_level: 'high', description: '' });

  // REVISI 1B: filter/sort state
  const [filterValues, setFilterValues] = useState({ is_active: '', attack_type: '' });
  const [sortBy, setSortBy] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');
  const [sandboxTab, setSandboxTab] = useState(0);
  const [payloadInput, setPayloadInput] = useState(DEFAULT_PAYLOAD);
  const [logInput, setLogInput] = useState(EXAMPLE_LOG_LINE);
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  const currentUser = useCurrentUser(); // REVISI 3B
  const isAdmin = currentUser?.role === 'admin';

  const SORT_OPTIONS = useMemo(() => [
    { value: 'created_at', label: t('rules.sortCreated') },
    { value: 'rule_name', label: t('rules.sortName') },
    { value: 'severity_level', label: t('rules.sortSeverity') },
    { value: 'match_count', label: t('rules.sortMatches') },
  ], [t]);

  const FILTER_CONFIG = useMemo(() => [
    {
      key: 'is_active',
      label: t('rules.filterStatus'),
      options: [
        { value: 'true', label: t('rules.active') },
        { value: 'false', label: t('rules.inactive') },
      ],
    },
    {
      key: 'attack_type',
      label: t('incidents.attackType'),
      options: ATTACK_TYPES.map((type) => ({ value: type, label: type.replace(/_/g, ' ') })),
    },
  ], [t]);

  const fetchRules = useCallback(async () => {
    setLoading(true);
    try {
      const params = { sort_by: sortBy, sort_dir: sortDir };
      if (filterValues.is_active !== '') params.is_active = filterValues.is_active;
      if (filterValues.attack_type) params.attack_type = filterValues.attack_type;
      const res = await getRules(params);
      setRules(res.data);
    } catch {
      toast.error('Failed to load rules');
    } finally {
      setLoading(false);
    }
  }, [sortBy, sortDir, filterValues]);

  useEffect(() => { fetchRules(); }, [fetchRules]);

  const handleFilterChange = (key, val) => {
    setFilterValues(prev => ({ ...prev, [key]: val }));
  };

  const handleClearFilters = () => {
    setFilterValues({ is_active: '', attack_type: '' });
    setSortBy('created_at');
    setSortDir('desc');
  };

  const hasActiveFilters = !!(filterValues.is_active || filterValues.attack_type);

  const handleSave = async () => {
    try {
      if (editRule) {
        await updateRule(editRule.id, form);
        toast.success('Rule updated');
      } else {
        await createRule(form);
        toast.success('Rule created');
      }
      setDialogOpen(false);
      setEditRule(null);
      setForm({ rule_name: '', attack_type: 'SQL_INJECTION', pattern: '', severity_level: 'high', description: '' });
      fetchRules();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed to save rule');
    }
  };

  const handleToggle = async (rule) => {
    try {
      await updateRule(rule.id, { is_active: !rule.is_active });
      toast.success(`Rule ${rule.is_active ? 'disabled' : 'enabled'}`);
      fetchRules();
    } catch { toast.error('Failed to update'); }
  };

  const handleDelete = async (id) => {
    try { await deleteRule(id); toast.success('Rule deleted'); fetchRules(); }
    catch { toast.error('Failed to delete'); }
  };

  const openEdit = (rule) => {
    setEditRule(rule);
    setForm({ rule_name: rule.rule_name, attack_type: rule.attack_type, pattern: rule.pattern, severity_level: rule.severity_level, description: rule.description });
    setDialogOpen(true);
  };

  const severityColors = { critical: '#ff1744', high: '#ff6d00', medium: '#ffd600', low: '#00e676' };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const body = sandboxTab === 0
        ? { payload: payloadInput, path: '/search', method: 'GET' }
        : { log_line: logInput };
      const res = await testPayload(body);
      setTestResult(res.data);
    } catch (e) {
      const errMsg = e.response?.data?.error || 'Test failed';
      const hint = sandboxTab === 1
        ? ' Hint: use a full nginx access log line (IP - - [date] "METHOD path HTTP/1.1" status size).'
        : '';
      setTestResult({ error: errMsg + hint });
    } finally {
      setTesting(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>{t('rules.title')}</Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary' }}>{t('rules.subtitle', { count: rules.filter(r => r.is_active).length })}</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {/* REVISI 3B: Add Rule hanya untuk admin */}
          {isAdmin && (
            <Button
              variant="outlined"
              startIcon={<Add />}
              onClick={() => { setEditRule(null); setDialogOpen(true); }}
              sx={{ borderColor: 'rgba(0,212,170,0.4)', color: 'primary.main' }}
            >
              {t('rules.addRule')}
            </Button>
          )}
          <IconButton onClick={fetchRules} sx={{ color: 'primary.main' }}><Refresh /></IconButton>
        </Box>
      </Box>

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
            <Science sx={{ color: 'secondary.main' }} />
            <Typography variant="h6">{t('rules.sandbox')}</Typography>
          </Box>
          <Tabs value={sandboxTab} onChange={(_, v) => { setSandboxTab(v); setTestResult(null); }} sx={{ mb: 2 }}>
            <Tab label={t('rules.tabPayload')} />
            <Tab label={t('rules.tabLog')} />
          </Tabs>
          {sandboxTab === 0 ? (
            <TextField
              fullWidth
              multiline
              minRows={2}
              label={t('rules.payloadLabel')}
              value={payloadInput}
              onChange={(e) => setPayloadInput(e.target.value)}
              placeholder={DEFAULT_PAYLOAD}
              sx={{ mb: 1.5, '& textarea': { fontFamily: 'monospace', fontSize: '0.8rem' } }}
            />
          ) : (
            <>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 1 }}>
                {t('rules.logExample')}
              </Typography>
              <TextField
                fullWidth
                multiline
                minRows={3}
                label={t('rules.logLabel')}
                value={logInput}
                onChange={(e) => setLogInput(e.target.value)}
                sx={{ mb: 1.5, '& textarea': { fontFamily: 'monospace', fontSize: '0.75rem' } }}
              />
            </>
          )}
          <Button
            variant="outlined"
            onClick={handleTest}
            disabled={testing || (sandboxTab === 0 ? !payloadInput.trim() : !logInput.trim())}
          >
            {testing ? t('rules.testing') : t('rules.test')}
          </Button>
          {testResult && (
            <Box sx={{ mt: 2, p: 1.5, borderRadius: 2, bgcolor: 'action.hover' }}>
              {testResult.error ? (
                <Typography color="error" variant="body2">{testResult.error}</Typography>
              ) : testResult.detected ? (
                <>
                  <Chip label={t('rules.detected')} color="error" size="small" sx={{ mb: 1 }} />
                  <Typography variant="body2">Attack: <strong>{testResult.threat?.attack_type}</strong></Typography>
                  <Typography variant="body2">Severity: <strong>{testResult.threat?.severity}</strong></Typography>
                  {testResult.threat?.rule_name && (
                    <Typography variant="body2">Rule: <strong>{testResult.threat.rule_name}</strong></Typography>
                  )}
                </>
              ) : (
                <Chip label={t('rules.noThreat')} size="small" />
              )}
            </Box>
          )}
        </CardContent>
      </Card>

      <FilterBar
        filters={FILTER_CONFIG}
        values={filterValues}
        onChange={handleFilterChange}
        sortOptions={SORT_OPTIONS}
        sortBy={sortBy}
        sortDir={sortDir}
        onSortBy={setSortBy}
        onSortDir={setSortDir}
        hasActiveFilters={hasActiveFilters}
        onClear={handleClearFilters}
      />

      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t('rules.colName')}</TableCell>
                <TableCell>{t('rules.colAttack')}</TableCell>
                <TableCell>{t('rules.colSeverity')}</TableCell>
                <TableCell>{t('rules.colPattern')}</TableCell>
                <TableCell>{t('rules.colMatches')}</TableCell>
                <TableCell align="center">{t('rules.colActive')}</TableCell>
                {isAdmin && <TableCell align="center">{t('common.actions')}</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={isAdmin ? 7 : 6} align="center" sx={{ py: 4 }}><CircularProgress size={28} /></TableCell></TableRow>
              ) : rules.map(rule => (
                <TableRow key={rule.id} hover>
                  <TableCell sx={{ fontWeight: 600 }}>{rule.rule_name}</TableCell>
                  <TableCell>
                    <Chip label={rule.attack_type.replace(/_/g, ' ')} size="small" variant="outlined"
                      sx={{ color: '#00d4aa', borderColor: 'rgba(0,212,170,0.3)', fontFamily: 'monospace', fontSize: '0.7rem' }} />
                  </TableCell>
                  <TableCell>
                    <Chip label={t(`severity.${rule.severity_level}`)} size="small"
                      sx={{ color: severityColors[rule.severity_level], bgcolor: `${severityColors[rule.severity_level]}22`, fontWeight: 700 }} />
                  </TableCell>
                  <TableCell>
                    <Typography sx={{ fontFamily: 'monospace', fontSize: '0.72rem', color: 'text.secondary', maxWidth: 200 }} noWrap>
                      {rule.pattern}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={rule.match_count || 0} size="small" sx={{ bgcolor: 'rgba(0,212,170,0.1)', color: 'primary.main' }} />
                  </TableCell>
                  <TableCell align="center">
                    {/* Toggle hanya berfungsi jika admin, analyst hanya lihat */}
                    <Switch
                      size="small"
                      checked={rule.is_active}
                      onChange={() => isAdmin && handleToggle(rule)}
                      color="primary"
                      disabled={!isAdmin}
                    />
                  </TableCell>
                  {/* REVISI 3B: Actions hanya untuk admin */}
                  {isAdmin && (
                    <TableCell align="center">
                      <Tooltip title={t('rules.edit')}><IconButton size="small" onClick={() => openEdit(rule)}><Edit sx={{ fontSize: 16, color: '#00d4aa' }} /></IconButton></Tooltip>
                      <Tooltip title={t('rules.delete')}><IconButton size="small" onClick={() => handleDelete(rule.id)}><Delete sx={{ fontSize: 16, color: '#ff4444' }} /></IconButton></Tooltip>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Dialog Create/Edit — hanya admin yang bisa buka */}
      {isAdmin && (
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>{editRule ? t('rules.editTitle') : t('rules.createTitle')}</DialogTitle>
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            <TextField fullWidth label={t('rules.ruleName')} value={form.rule_name} onChange={e => setForm(f => ({ ...f, rule_name: e.target.value }))} />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <FormControl fullWidth>
                <InputLabel>{t('incidents.attackType')}</InputLabel>
                <Select value={form.attack_type} label={t('incidents.attackType')} onChange={e => setForm(f => ({ ...f, attack_type: e.target.value }))}>
                  {ATTACK_TYPES.map(t =>
                    <MenuItem key={t} value={t}>{t.replace(/_/g, ' ')}</MenuItem>
                  )}
                </Select>
              </FormControl>
              <FormControl fullWidth>
                <InputLabel>{t('incidents.severity')}</InputLabel>
                <Select value={form.severity_level} label={t('incidents.severity')} onChange={e => setForm(f => ({ ...f, severity_level: e.target.value }))}>
                  {['critical', 'high', 'medium', 'low'].map(s => <MenuItem key={s} value={s}>{t(`severity.${s}`)}</MenuItem>)}
                </Select>
              </FormControl>
            </Box>
            <TextField fullWidth label={t('rules.pattern')} value={form.pattern} onChange={e => setForm(f => ({ ...f, pattern: e.target.value }))}
              sx={{ '& input': { fontFamily: 'monospace' } }} placeholder="(?i)(union\s+select|select\s+.*\s+from)" />
            <TextField fullWidth label={t('rules.description')} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} multiline rows={2} />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>{t('common.cancel')}</Button>
            <Button variant="contained" onClick={handleSave} disabled={!form.rule_name || !form.pattern}>
              {editRule ? t('rules.update') : t('rules.create')}
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </Box>
  );
}

export default DetectionRules;
