import React from 'react';
import { Chip, Tooltip, useTheme } from '@mui/material';
import { GppBad } from '@mui/icons-material';
import { useLanguage } from '../../context/LanguageContext';

/** Shared chip styling from semantic tokens (border + readable text in light/dark). */
export function chipSx(config, extra = {}) {
  if (!config) return extra;
  return {
    color: config.color,
    bgcolor: config.bg,
    border: config.border ? `1px solid ${config.border}` : undefined,
    fontWeight: 700,
    fontSize: '0.7rem',
    ...extra,
  };
}

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
        border: config.border ? `1px solid ${config.border}` : undefined,
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
        border: config.border ? `1px solid ${config.border}` : undefined,
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
      sx={{
        color: atk?.color,
        bgcolor: atk?.bg,
        border: `1px solid ${atk?.border}`,
        fontSize: '0.7rem',
        fontWeight: 600,
        fontFamily: 'monospace',
        letterSpacing: '0.02em',
      }}
    />
  );
}

export function RepeatOffenderChip({ size = 'small', tooltip }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const config = theme.semantic?.repeatOffender;
  const chip = (
    <Chip
      icon={<GppBad sx={{ fontSize: 14 }} />}
      label={t('blockedIps.repeatOffender')}
      size={size}
      sx={{
        color: config?.color,
        bgcolor: config?.bg,
        border: `1px solid ${config?.border}`,
        fontWeight: 700,
        fontSize: '0.65rem',
        height: 22,
        '& .MuiChip-icon': { color: config?.color },
      }}
    />
  );
  if (tooltip) {
    return <Tooltip title={tooltip}>{chip}</Tooltip>;
  }
  return chip;
}

export function BlockTypeChip({ blockType, size = 'small' }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const sem = theme.semantic;
  const config = blockType === 'permanent' ? sem?.chipBlocked : sem?.chipTemporary;
  return (
    <Chip
      label={t(`blockType.${blockType}`)}
      size={size}
      sx={chipSx(config)}
    />
  );
}

/** Expiry / TTL chips — active (amber), expired (muted), never (red). */
export function ExpiryChip({ variant = 'active', label, tooltip, size = 'small' }) {
  const theme = useTheme();
  const sem = theme.semantic;
  const configByVariant = {
    active: sem?.chipTemporary,
    expired: sem?.chipExpired,
    never: sem?.chipBlocked,
  };
  const chip = (
    <Chip label={label} size={size} sx={chipSx(configByVariant[variant] || sem?.chipTemporary)} />
  );
  if (tooltip) {
    return <Tooltip title={tooltip}>{chip}</Tooltip>;
  }
  return chip;
}

/** Settings integration status — configured vs not set. */
export function ConfigStatusChip({ configured, size = 'small' }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const config = configured ? theme.semantic?.chipConfigured : theme.semantic?.chipNotConfigured;
  return (
    <Chip
      label={configured ? `● ${t('common.configured')}` : `○ ${t('common.notSet')}`}
      size={size}
      sx={chipSx(config, { fontWeight: 600 })}
    />
  );
}

/** Numeric badge chips (incident count, rule matches). */
export function MetricChip({ label, variant = 'incident', size = 'small' }) {
  const theme = useTheme();
  const sem = theme.semantic;
  const config = variant === 'count' ? sem?.attackType : sem?.chipIncident;
  return <Chip label={label} size={size} sx={chipSx(config, { fontWeight: 600 })} />;
}
