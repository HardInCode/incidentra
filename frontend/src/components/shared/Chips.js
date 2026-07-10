import React from 'react';
import { Chip, useTheme } from '@mui/material';
import { useLanguage } from '../../context/LanguageContext';

export function SeverityChip({ severity, size = 'small' }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const config = theme.semantic?.severity?.[severity] || theme.semantic?.severity?.low;
  const label = severity ? t(`severity.${severity}`) : t('severity.low');
  return (
    <Chip
      label={label}
      size={size}
      sx={{
        color: config.color,
        bgcolor: config.bg,
        border: `1px solid ${config.border}`,
        fontWeight: 700,
        fontSize: '0.7rem',
        letterSpacing: '0.03em',
      }}
    />
  );
}

export function StatusChip({ status, size = 'small' }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const config = theme.semantic?.status?.[status] || theme.semantic?.status?.new;
  const label = status ? t(`status.${status}`) : t('status.new');
  return (
    <Chip
      label={label}
      size={size}
      sx={{
        color: config.color,
        bgcolor: config.bg,
        fontWeight: 600,
        fontSize: '0.7rem',
      }}
    />
  );
}

export function AccountStatusChip({ status, size = 'small' }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const config = theme.semantic?.accountStatus?.[status] || theme.semantic?.accountStatus?.pending;
  const label = t(`accountStatus.${status || 'pending'}`);
  return (
    <Chip
      label={label}
      size={size}
      sx={{
        color: config.color,
        bgcolor: config.bg,
        fontWeight: 700,
        fontSize: '0.7rem',
        letterSpacing: '0.03em',
      }}
    />
  );
}

export function AttackTypeChip({ type, size = 'small' }) {
  const theme = useTheme();
  const atk = theme.semantic?.attackType;
  const label = type?.replace(/_/g, ' ') || 'Unknown';
  return (
    <Chip
      label={label}
      size={size}
      variant="outlined"
      sx={{
        color: atk?.color,
        borderColor: atk?.border,
        fontSize: '0.7rem',
        fontWeight: 600,
        fontFamily: 'monospace',
      }}
    />
  );
}
