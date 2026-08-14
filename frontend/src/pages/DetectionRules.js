/**
 * DETECTION RULES PAGE — CRUD rule analyst + sandbox test regex.
 * Ctrl+F: RULES_FLOW, handleSave, handleTest, ATTACK_TYPES
 *
 * Alur tambah rule (hulu → hilir):
 *   handleSave → api.createRule → backend rules.py create_rule → PostgreSQL detection_rules
 *   → Redis rules_dirty → detection_engine reload → log_monitor analyze() pakai regex baru
 *
 * Pasangan backend:
 *   backend/app/api/rules.py          (CRUD + rules_dirty)
 *   backend/app/core/detection_engine.py (_load_rules_from_db, analyze)
 *   backend/app/api/detection.py      (sandbox /test)
 *   frontend/src/constants/attackTypes.js (dropdown attack_type)
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box, Card, CardContent, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Button, TextField, Dialog,
  DialogTitle, DialogContent, DialogActions, Switch, Chip, IconButton,
  Tooltip, CircularProgress, Select, MenuItem, FormControl, InputLabel,
  Tabs, Tab,
} from '@mui/material';
import { Add, Delete, Edit, Refresh, Science, InfoOutlined } from '@mui/icons-material';
import { toast } from 'react-toastify';
import { getRules, createRule, updateRule, deleteRule, testPayload, getSettings } from '../services/api';
import FilterBar from '../components/shared/FilterBar';
import useCurrentUser from '../hooks/useCurrentUser';
import { useLanguage } from '../context/LanguageContext';

import { ATTACK_TYPES } from '../constants/attackTypes';  // 9 tipe — sync DETECTION_PATTERNS backend
import { brandCyan, brandAlpha } from '../theme';

const DEFAULT_PAYLOAD = "' OR 1=1--";
const EXAMPLE_LOG_LINE = '192.168.1.50 - - [15/May/2026:10:30:00 +0000] "GET /search?q=\'+OR+1=1+UNION+SELECT+username,password+FROM+users-- HTTP/1.1" 200 512 "-" "sqlmap/1.7"';

export function DetectionRules() {
  const { t } = useLanguage();
  const [rules, setRules] = useState([]);           // rows dari GET /api/rules/
  const [loading, setLoading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editRule, setEditRule] = useState(null);   // null = create, object = edit
  // form → dikirim ke createRule/updateRule — field harus match DetectionRule model backend
  const [form, setForm] = useState({
    rule_name: '',
    attack_type: 'SQL_INJECTION',
    pattern: '',
    severity_level: 'high',
    description: '',
  });

  const [filterValues, setFilterValues] = useState({ is_active: '', attack_type: '' });
  const [sortBy, setSortBy] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');
  const [sandboxTab, setSandboxTab] = useState(0);   // 0=payload, 1=full log line
  const [payloadInput, setPayloadInput] = useState(DEFAULT_PAYLOAD);
  const [logInput, setLogInput] = useState(EXAMPLE_LOG_LINE);
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const [labModeOnly, setLabModeOnly] = useState(false);  // true = OWASP baseline OFF di engine

  const currentUser = useCurrentUser();
  const isAdmin = currentUser?.role === 'admin';  // CRUD cuma admin; analyst read-only

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

  // ─── RULES_FLOW: baca list rule dari PostgreSQL via GET /api/rules/ ───
  const fetchRules = useCallback(async () => {
    setLoading(true);
    try {
      const params = { sort_by: sortBy, sort_dir: sortDir };
      if (filterValues.is_active !== '') params.is_active = filterValues.is_active;
      if (filterValues.attack_type) params.attack_type = filterValues.attack_type;
      const res = await getRules(params);  // api.js → rules.py list_rules()
      setRules(res.data);
    } catch {
      toast.error('Failed to load rules');
    } finally {
      setLoading(false);
    }
  }, [sortBy, sortDir, filterValues]);

  useEffect(() => { fetchRules(); }, [fetchRules]);

  // Lab mode: kalau ON, engine cuma pakai rule UI — baseline OWASP (DETECTION_PATTERNS) dimatikan
  useEffect(() => {
    getSettings().then((res) => {
      const raw = res.data?.DETECTION_LAB_MODE_UI_ONLY?.value || '';
      setLabModeOnly(['true', '1', 'yes', 'on'].includes(String(raw).toLowerCase()));
    }).catch(() => {});
  }, []);

  const handleFilterChange = (key, val) => {
    setFilterValues(prev => ({ ...prev, [key]: val }));
  };

  const handleClearFilters = () => {
    setFilterValues({ is_active: '', attack_type: '' });
    setSortBy('created_at');
    setSortDir('desc');
  };

  const hasActiveFilters = !!(filterValues.is_active || filterValues.attack_type);

  // ─── RULES_FLOW step 1 UI: POST/PUT rule → rules.py → rules_dirty → engine reload ───
  const handleSave = async () => {
    try {
      if (editRule) {
        await updateRule(editRule.id, form);  // PUT /api/rules/:id
        toast.success('Rule updated');
      } else {
        await createRule(form);  // POST /api/rules/ — pattern disimpan ke detection_rules
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
      await updateRule(rule.id, { is_active: !rule.is_active });  // nonaktifkan rule tanpa delete
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
    setForm({
      rule_name: rule.rule_name,
      attack_type: rule.attack_type,
      pattern: rule.pattern,
      severity_level: rule.severity_level,
      description: rule.description,
    });
    setDialogOpen(true);
  };

  const severityColors = { critical: '#ff1744', high: '#ff6d00', medium: '#ffd600', low: '#00e676' };

  // ─── Sandbox: test regex TANPA INSERT incident — detection.py test_payload → analyze() ───
  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const body = sandboxTab === 0
        ? { payload: payloadInput, path: '/search', method: 'GET' }  // tab Payload
        : { log_line: logInput };                                      // tab Log line
      const res = await testPayload(body);  // POST /api/detection/test
      setTestResult(res.data);              // { detected, threat: { attack_type, severity } }
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
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          {isAdmin && (
            <Button
              variant="outlined"
              startIcon={<Add />}
              onClick={() => { setEditRule(null); setDialogOpen(true); }}
              sx={{ borderColor: brandAlpha(0.4), color: 'primary.main' }}
            >
              {t('rules.addRule')}
            </Button>
          )}
          <Tooltip
            title={labModeOnly ? t('rules.labModeOn') : t('rules.baselineActive')}
            placement="bottom"
            arrow
            slotProps={{ tooltip: { sx: { maxWidth: 360, fontSize: '0.8rem' } } }}
          >
            <IconButton size="small" aria-label={t('rules.detectionInfo')} sx={{ color: 'text.secondary' }}>
              <InfoOutlined fontSize="small" />
            </IconButton>
          </Tooltip>
          <IconButton onClick={fetchRules} sx={{ color: 'primary.main' }}><Refresh /></IconButton>
        </Box>
      </Box>

      {/* Sandbox — admin only; preview match sebelum rule dipakai log_monitor */}
      {isAdmin && (
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
      )}

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
                <TableCell>{t('rules.colMatches')}</TableCell>  {/* match_count dari log_monitor saat rule kena */}
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
                      sx={{ color: brandCyan.main, borderColor: brandAlpha(0.3), fontFamily: 'monospace', fontSize: '0.7rem' }} />
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
                    <Chip label={rule.match_count || 0} size="small" sx={{ bgcolor: brandAlpha(0.1), color: 'primary.main' }} />
                  </TableCell>
                  <TableCell align="center">
                    <Switch
                      size="small"
                      checked={rule.is_active}
                      onChange={() => isAdmin && handleToggle(rule)}
                      color="primary"
                      disabled={!isAdmin}
                    />
                  </TableCell>
                  {isAdmin && (
                    <TableCell align="center">
                      <Tooltip title={t('rules.edit')}><IconButton size="small" onClick={() => openEdit(rule)}><Edit sx={{ fontSize: 16, color: brandCyan.main }} /></IconButton></Tooltip>
                      <Tooltip title={t('rules.delete')}><IconButton size="small" onClick={() => handleDelete(rule.id)}><Delete sx={{ fontSize: 16, color: '#ff4444' }} /></IconButton></Tooltip>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Dialog create/edit — attack_type dari ATTACK_TYPES; pattern → regex di engine */}
      {isAdmin && (
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle>{editRule ? t('rules.editTitle') : t('rules.createTitle')}</DialogTitle>
          <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 3, px: 3, pb: 1 }}>
            <TextField
              fullWidth
              margin="normal"
              label={t('rules.ruleName')}
              value={form.rule_name}
              onChange={e => setForm(f => ({ ...f, rule_name: e.target.value }))}
              InputLabelProps={{ shrink: true }}
            />
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
            <TextField
              fullWidth
              margin="normal"
              label={t('rules.pattern')}
              value={form.pattern}
              onChange={e => setForm(f => ({ ...f, pattern: e.target.value }))}
              InputLabelProps={{ shrink: true }}
              sx={{ '& input': { fontFamily: 'monospace' } }}
              placeholder="(?i)(union\s+select|select\s+.*\s+from)"
            />
            <TextField
              fullWidth
              margin="normal"
              label={t('rules.description')}
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              InputLabelProps={{ shrink: true }}
              multiline
              rows={2}
            />
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
