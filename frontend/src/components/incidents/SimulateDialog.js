/**
 * SIMULATE / INJECT DIALOG — admin demo serangan dari Incidents page.
 * Ctrl+F: SIMULATE_FLOW, INJECT_FLOW
 *
 * Mode Direct  → simulateAttack → detection.py /simulate (INSERT + respond, bypass log)
 * Mode Inject  → injectLog      → detection.py /inject-log (PIPELINE penuh via access.log)
 */
import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Box, Typography, Select, MenuItem, FormControl, InputLabel, TextField,
  Alert, RadioGroup, FormControlLabel, Radio, Chip, useTheme,
} from '@mui/material';
import { PlayArrow, Terminal, DirectionsRun } from '@mui/icons-material';
import { injectLog } from '../../services/api';
import { toast } from 'react-toastify';

import { SIMULATE_ATTACK_TYPES } from '../../constants/attackTypes';
import { brandCyan, brandAlpha } from '../../theme';

const SEVERITY_COLORS = { Critical: '#ff1744', High: '#ff6d00', Medium: '#ffd600' };

export default function SimulateDialog({ open, onClose, onSimulate, onInjectSuccess }) {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const inset = theme.semantic?.insetPanel;
  const [attackType, setAttackType] = useState('SQL_INJECTION');
  const [ip, setIp] = useState('45.33.32.156');  // scanme.nmap.org — safe public test IP
  const [mode, setMode] = useState('direct');
  const [injecting, setInjecting] = useState(false);

  const selected = SIMULATE_ATTACK_TYPES.find(a => a.value === attackType);

  const handleLaunch = async () => {
    if (mode === 'inject') {
      setInjecting(true);
      try {
        const res = await injectLog({ attack_type: attackType, ip });
        const msg = res.data?.message || 'Log injected';
        const ids = res.data?.incident_ids || [];
        if (ids.length > 0) {
          toast.success(msg, { autoClose: 5000 });
        } else {
          toast.warn(msg, { autoClose: 8000 });
        }
        onClose();
        onInjectSuccess?.(ids);
      } catch (e) {
        toast.error(e.response?.data?.error || 'Log injection failed');
      } finally {
        setInjecting(false);
      }
    } else {
      onSimulate({ attack_type: attackType, ip });
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PlayArrow sx={{ color: '#7c4dff' }} />
          Simulate Attack
        </Box>
      </DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
        <Box sx={{
          p: 2,
          bgcolor: inset?.bg ?? 'action.hover',
          borderRadius: 2,
          border: 1,
          borderColor: inset?.border ?? 'divider',
        }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', textTransform: 'uppercase', fontWeight: 700, mb: 1, display: 'block' }}>
            Simulation Mode
          </Typography>
          <RadioGroup value={mode} onChange={e => setMode(e.target.value)}>
            <FormControlLabel
              value="direct"
              control={<Radio size="small" sx={{ color: '#7c4dff', '&.Mui-checked': { color: '#7c4dff' } }} />}
              label={
                <Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <DirectionsRun sx={{ fontSize: 16, color: '#7c4dff' }} />
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>Mode A — Direct Simulation</Typography>
                    <Chip label="Instant" size="small" sx={{ bgcolor: 'rgba(124,77,255,0.15)', color: '#7c4dff', fontSize: '0.65rem' }} />
                  </Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', pl: 3, display: 'block' }}>
                    Creates incident directly in DB. Bypasses detection engine. Good for UI testing.
                  </Typography>
                </Box>
              }
            />
            <FormControlLabel
              value="inject"
              control={<Radio size="small" sx={{ color: brandCyan.main, '&.Mui-checked': { color: brandCyan.main } }} />}
              label={
                <Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Terminal sx={{ fontSize: 16, color: brandCyan.main }} />
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>Mode B — Log Injection</Typography>
                    <Chip label="Realistic" size="small" sx={{ bgcolor: brandAlpha(0.12, isDark), color: brandCyan.main, fontSize: '0.65rem' }} />
                  </Box>
                  <Typography variant="caption" sx={{ color: 'text.secondary', pl: 3, display: 'block' }}>
                    Writes to access.log and runs the full detection pipeline immediately. Change IP if you see a duplicate warning.
                  </Typography>
                </Box>
              }
            />
          </RadioGroup>
        </Box>

        <FormControl fullWidth>
          <InputLabel>Attack Type</InputLabel>
          <Select value={attackType} label="Attack Type" onChange={e => setAttackType(e.target.value)}>
            {SIMULATE_ATTACK_TYPES.map(a => (
              <MenuItem key={a.value} value={a.value}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                  <span>{a.label}</span>
                  <span style={{ fontSize: '0.72rem', color: SEVERITY_COLORS[a.severity], fontWeight: 700 }}>{a.severity}</span>
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {selected && (
          <Box sx={{
            p: 2,
            bgcolor: isDark ? 'rgba(124,77,255,0.08)' : 'rgba(124,77,255,0.06)',
            borderRadius: 2,
            border: 1,
            borderColor: isDark ? 'rgba(124,77,255,0.2)' : 'rgba(124,77,255,0.15)',
          }}>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>{selected.desc}</Typography>
          </Box>
        )}

        <TextField
          fullWidth label="Source IP (simulated)"
          value={ip}
          onChange={e => setIp(e.target.value)}
          placeholder="45.33.32.156"
          sx={{ '& input': { fontFamily: 'monospace' } }}
        />

        {mode === 'inject' ? (
          <Alert severity="success" sx={{ fontSize: '0.82rem' }}>
            💡 <strong>Real Pipeline Test:</strong> Writes to access.log and runs the detection engine immediately. The list refreshes automatically.
          </Alert>
        ) : (
          <Alert severity="info" sx={{ fontSize: '0.82rem' }}>
            Creates an incident directly in the database. No real attack is performed and the detection engine is bypassed.
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          startIcon={<PlayArrow />}
          onClick={handleLaunch}
          disabled={injecting}
          color={mode === 'inject' ? 'primary' : 'secondary'}
        >
          {injecting ? 'Injecting...' : mode === 'inject' ? 'Inject Log' : 'Launch Simulation'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
