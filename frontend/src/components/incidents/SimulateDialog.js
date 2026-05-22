import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Box, Typography, Select, MenuItem, FormControl, InputLabel, TextField,
  Alert, RadioGroup, FormControlLabel, Radio, Chip,
} from '@mui/material';
import { PlayArrow, Terminal, DirectionsRun } from '@mui/icons-material';
import { injectLog } from '../../services/api';
import { toast } from 'react-toastify';

const ATTACK_TYPES = [
  { value: 'SQL_INJECTION', label: 'SQL Injection', severity: 'Critical', desc: 'Simulates a UNION-based SQL injection attempt' },
  { value: 'XSS', label: 'Cross-Site Scripting', severity: 'High', desc: 'Simulates a script tag XSS injection' },
  { value: 'BRUTE_FORCE', label: 'Brute Force', severity: 'High', desc: 'Simulates multiple failed login attempts' },
  { value: 'PATH_TRAVERSAL', label: 'Path Traversal', severity: 'High', desc: 'Simulates directory traversal attack' },
  { value: 'COMMAND_INJECTION', label: 'Command Injection', severity: 'Critical', desc: 'Simulates OS command injection' },
  { value: 'SCANNER', label: 'Security Scanner', severity: 'Medium', desc: 'Simulates automated vulnerability scanner' },
  { value: 'LFI_RFI', label: 'LFI/RFI', severity: 'Critical', desc: 'Simulates PHP file inclusion attack' },
  { value: 'FILE_UPLOAD', label: 'File Upload', severity: 'High', desc: 'Simulates POST /files with uploaded filename in log' },
];

const SEVERITY_COLORS = { Critical: '#ff1744', High: '#ff6d00', Medium: '#ffd600' };

export default function SimulateDialog({ open, onClose, onSimulate, onInjectSuccess }) {
  const [attackType, setAttackType] = useState('SQL_INJECTION');
  const [ip, setIp] = useState('45.33.32.156');  // scanme.nmap.org — safe public test IP
  const [mode, setMode] = useState('direct');
  const [injecting, setInjecting] = useState(false);

  const selected = ATTACK_TYPES.find(a => a.value === attackType);

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
        <Box sx={{ p: 2, bgcolor: 'rgba(0,0,0,0.3)', borderRadius: 2, border: '1px solid rgba(255,255,255,0.08)' }}>
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
              control={<Radio size="small" sx={{ color: '#00d4aa', '&.Mui-checked': { color: '#00d4aa' } }} />}
              label={
                <Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Terminal sx={{ fontSize: 16, color: '#00d4aa' }} />
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>Mode B — Log Injection</Typography>
                    <Chip label="Realistic" size="small" sx={{ bgcolor: 'rgba(0,212,170,0.12)', color: '#00d4aa', fontSize: '0.65rem' }} />
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
            {ATTACK_TYPES.map(a => (
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
          <Box sx={{ p: 2, bgcolor: 'rgba(124,77,255,0.08)', borderRadius: 2, border: '1px solid rgba(124,77,255,0.2)' }}>
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
