import React, { useMemo, useState } from 'react';
import {
  FormControl, InputLabel, Select, MenuItem, Popover, Box, TextField, Button,
  IconButton, Tooltip,
} from '@mui/material';
import { EditCalendar } from '@mui/icons-material';
import { toast } from 'react-toastify';
import { useLanguage } from '../../context/LanguageContext';
import {
  getDateRange,
  isoToDatetimeLocal,
  datetimeLocalToIso,
  normalizeCustomRange,
  startOfLocalDayIso,
  endOfLocalDayIso,
} from '../../utils/dateRange';

export const DATE_PRESET_VALUES = ['all', 'today', '7d', '30d', 'custom'];

export function useDatePresetOptions() {
  const { t } = useLanguage();
  return useMemo(() => DATE_PRESET_VALUES.map((value) => ({
    value,
    label: t(`dateRange.${value}`),
  })), [t]);
}

export { getDateRange };

export default function DateRangeFilter({
  preset,
  dateFrom,
  dateTo,
  onPresetChange,
  onApply,
}) {
  const { t } = useLanguage();
  const presetOptions = useDatePresetOptions();
  const [anchor, setAnchor] = useState(null);
  const [draftFrom, setDraftFrom] = useState('');
  const [draftTo, setDraftTo] = useState('');

  const openCustomPopover = () => {
    const now = new Date();
    setDraftFrom(isoToDatetimeLocal(dateFrom) || isoToDatetimeLocal(startOfLocalDayIso(now)));
    setDraftTo(
      isoToDatetimeLocal(dateTo)
      || isoToDatetimeLocal(endOfLocalDayIso(now.toISOString())),
    );
    setAnchor(document.getElementById('date-range-filter-anchor'));
  };

  const handlePreset = (value) => {
    onPresetChange(value);
    if (value === 'custom') {
      openCustomPopover();
      return;
    }
    setAnchor(null);
    const range = getDateRange(value);
    onApply?.(range.date_from, range.date_to);
  };

  const applyCustom = () => {
    const fromIso = datetimeLocalToIso(draftFrom);
    const toIso = datetimeLocalToIso(draftTo);
    if (!fromIso || !toIso) {
      toast.warn(t('dateRange.needBoth'));
      return;
    }
    const { date_from, date_to, swapped } = normalizeCustomRange(fromIso, toIso);
    if (swapped) {
      toast.info(t('dateRange.swapped'));
    }
    setAnchor(null);
    onApply?.(date_from, date_to);
  };

  return (
    <>
      <Box
        id="date-range-filter-anchor"
        sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}
      >
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>{t('dateRange.label')}</InputLabel>
          <Select
            value={preset}
            label={t('dateRange.label')}
            onChange={(e) => handlePreset(e.target.value)}
          >
            {presetOptions.map((opt) => (
              <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
            ))}
          </Select>
        </FormControl>
        {preset === 'custom' && (
          <Tooltip title={t('dateRange.edit')}>
            <IconButton size="small" onClick={openCustomPopover} sx={{ color: 'primary.main' }}>
              <EditCalendar fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>
      <Popover
        open={Boolean(anchor) && preset === 'custom'}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      >
        <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1.5, minWidth: 280 }}>
          <TextField
            size="small"
            type="datetime-local"
            label={t('dateRange.from')}
            value={draftFrom}
            onChange={(e) => setDraftFrom(e.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <TextField
            size="small"
            type="datetime-local"
            label={t('dateRange.to')}
            value={draftTo}
            onChange={(e) => setDraftTo(e.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <Button size="small" variant="contained" onClick={applyCustom}>
            {t('dateRange.apply')}
          </Button>
        </Box>
      </Popover>
    </>
  );
}
