import { createTheme } from '@mui/material';

export const THEME_STORAGE_KEY = 'incidentra-theme';

/** Vivid cyan — primary brand accent (replaces former teal #00d4aa). */
export const brandCyan = {
  main: '#00c7d4',
  dark: '#00a3ad',
  light: '#00a8b3',
  rgb: '0, 199, 212',
  rgbLight: '0, 168, 179',
};

export function brandAlpha(alpha, isDark = true) {
  const rgb = isDark ? brandCyan.rgb : brandCyan.rgbLight;
  return `rgba(${rgb}, ${alpha})`;
}

export const severityColors = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#ca8a04',
  low: '#059669',
};

export const iconSize = {
  nav: 24,
  action: 22,
  inline: 20,
  dense: 18,
};

export const tokens = {
  borderRadius: 10,
  cardRadius: 12,
  iconSize: iconSize.nav,
};

export function resolveMode(preference) {
  if (preference === 'light' || preference === 'dark') return preference;
  if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

export function getStoredThemePreference() {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY) || 'dark';
  } catch {
    return 'dark';
  }
}

export function getInitialMode() {
  return resolveMode(getStoredThemePreference());
}

/** Theme-aware semantic tokens for alerts, chips, and nav (light/dark). */
export function getSemanticTokens(isDark) {
  return {
    alertSuccess: {
      bg: isDark ? 'rgba(52,211,153,0.14)' : '#ecfdf5',
      border: isDark ? 'rgba(52,211,153,0.35)' : '#a7f3d0',
      color: isDark ? '#6ee7b7' : '#065f46',
    },
    alertWarning: {
      bg: isDark ? 'rgba(234,179,8,0.14)' : '#fefce8',
      border: isDark ? 'rgba(234,179,8,0.35)' : '#fde68a',
      color: isDark ? '#fde047' : '#854d0e',
    },
    alertError: {
      bg: isDark ? 'rgba(239,68,68,0.14)' : '#fef2f2',
      border: isDark ? 'rgba(239,68,68,0.35)' : '#fecaca',
      color: isDark ? '#fca5a5' : '#991b1b',
    },
    chipBlocked: {
      bg: isDark ? 'rgba(239,68,68,0.16)' : '#fef2f2',
      color: isDark ? '#fca5a5' : '#991b1b',
      border: isDark ? 'rgba(239,68,68,0.35)' : '#fecaca',
    },
    chipTemporary: {
      bg: isDark ? 'rgba(234,179,8,0.14)' : '#fefce8',
      color: isDark ? '#fde047' : '#854d0e',
      border: isDark ? 'rgba(234,179,8,0.35)' : '#fde68a',
    },
    chipExpired: {
      bg: isDark ? 'rgba(148,163,184,0.14)' : '#f1f5f9',
      color: isDark ? '#94a3b8' : '#475569',
      border: isDark ? 'rgba(148,163,184,0.3)' : '#e2e8f0',
    },
    chipIncident: {
      bg: isDark ? 'rgba(249,115,22,0.14)' : '#fff7ed',
      color: isDark ? '#fdba74' : '#9a3412',
      border: isDark ? 'rgba(249,115,22,0.35)' : '#fed7aa',
    },
    navActive: {
      bg: isDark ? brandAlpha(0.12, true) : brandAlpha(0.08, false),
      border: isDark ? brandAlpha(0.25, true) : brandAlpha(0.22, false),
    },
    navHover: {
      bg: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(15,23,42,0.04)',
    },
    chipAdmin: {
      color: isDark ? '#fdba74' : '#9a3412',
      bg: isDark ? 'rgba(249,115,22,0.14)' : '#fff7ed',
      borderColor: isDark ? 'rgba(249,115,22,0.35)' : '#fed7aa',
    },
    chipAnalyst: {
      color: isDark ? '#67e8f9' : '#0e7490',
      bg: isDark ? 'rgba(34,211,238,0.12)' : '#ecfeff',
      borderColor: isDark ? 'rgba(34,211,238,0.3)' : '#a5f3fc',
    },
    accountStatus: {
      pending: {
        color: isDark ? '#fde047' : '#854d0e',
        bg: isDark ? 'rgba(234,179,8,0.14)' : '#fefce8',
        border: isDark ? 'rgba(234,179,8,0.35)' : '#fde68a',
      },
      active: {
        color: isDark ? '#6ee7b7' : '#065f46',
        bg: isDark ? 'rgba(52,211,153,0.14)' : '#ecfdf5',
        border: isDark ? 'rgba(52,211,153,0.35)' : '#a7f3d0',
      },
      suspended: {
        color: isDark ? '#fca5a5' : '#991b1b',
        bg: isDark ? 'rgba(239,68,68,0.14)' : '#fef2f2',
        border: isDark ? 'rgba(239,68,68,0.35)' : '#fecaca',
      },
    },
    severity: {
      critical: {
        color: isDark ? '#fca5a5' : '#991b1b',
        bg: isDark ? 'rgba(239,68,68,0.16)' : '#fee2e2',
        border: isDark ? 'rgba(239,68,68,0.35)' : '#fecaca',
      },
      high: {
        color: isDark ? '#fdba74' : '#9a3412',
        bg: isDark ? 'rgba(249,115,22,0.16)' : '#ffedd5',
        border: isDark ? 'rgba(249,115,22,0.35)' : '#fed7aa',
      },
      medium: {
        color: isDark ? '#fde047' : '#854d0e',
        bg: isDark ? 'rgba(234,179,8,0.14)' : '#fef9c3',
        border: isDark ? 'rgba(234,179,8,0.35)' : '#fde047',
      },
      low: {
        color: isDark ? '#6ee7b7' : '#065f46',
        bg: isDark ? 'rgba(52,211,153,0.14)' : '#d1fae5',
        border: isDark ? 'rgba(52,211,153,0.35)' : '#a7f3d0',
      },
    },
    status: {
      new: {
        color: isDark ? '#a5b4fc' : '#3730a3',
        bg: isDark ? 'rgba(99,102,241,0.16)' : '#e0e7ff',
        border: isDark ? 'rgba(99,102,241,0.35)' : '#c7d2fe',
      },
      investigating: {
        color: isDark ? '#7dd3fc' : '#0369a1',
        bg: isDark ? 'rgba(14,165,233,0.16)' : '#e0f2fe',
        border: isDark ? 'rgba(14,165,233,0.35)' : '#bae6fd',
      },
      resolved: {
        color: isDark ? '#6ee7b7' : '#065f46',
        bg: isDark ? 'rgba(52,211,153,0.14)' : '#ecfdf5',
        border: isDark ? 'rgba(52,211,153,0.35)' : '#a7f3d0',
      },
      false_positive: {
        color: isDark ? '#94a3b8' : '#475569',
        bg: isDark ? 'rgba(148,163,184,0.14)' : '#f1f5f9',
        border: isDark ? 'rgba(148,163,184,0.3)' : '#e2e8f0',
      },
    },
    attackType: {
      color: isDark ? '#cbd5e1' : '#475569',
      bg: isDark ? 'rgba(148,163,184,0.1)' : '#f8fafc',
      border: isDark ? 'rgba(148,163,184,0.35)' : '#cbd5e1',
    },
    surfaceMuted: {
      bg: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)',
      border: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)',
    },
    insetPanel: {
      bg: isDark ? 'rgba(0,0,0,0.25)' : 'rgba(0,0,0,0.04)',
      border: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)',
    },
    codeBlock: {
      bg: isDark ? 'rgba(0,0,0,0.35)' : 'rgba(0,0,0,0.05)',
      color: isDark ? brandCyan.main : brandCyan.dark,
    },
    notePanel: {
      bg: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)',
    },
  };
}

function sharedTypography() {
  return {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  };
}

function sharedComponents(mode) {
  const border = mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)';
  const headColor = mode === 'dark' ? '#8892a4' : '#5f6b7a';
  return {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          border: `1px solid ${border}`,
          borderRadius: tokens.cardRadius,
          ...(mode === 'dark' ? { backdropFilter: 'blur(10px)' } : {}),
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, fontSize: '0.72rem' },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', fontWeight: 600, borderRadius: tokens.borderRadius },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 700,
          color: headColor,
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: `1px solid ${border}`,
        },
      },
    },
    MuiListItemIcon: {
      styleOverrides: {
        root: {
          minWidth: 40,
          '& svg': { fontSize: iconSize.nav },
        },
      },
    },
  };
}

export function createAppTheme(mode = 'dark') {
  const isDark = mode === 'dark';
  const semantic = getSemanticTokens(isDark);
  return createTheme({
    iconSize,
    semantic,
    palette: {
      mode,
      primary: {
        main: isDark ? brandCyan.main : brandCyan.light,
        dark: brandCyan.dark,
        light: brandCyan.main,
        contrastText: isDark ? '#0a0e1a' : '#ffffff',
      },
      secondary: { main: '#6366f1' },
      error: { main: '#dc2626' },
      warning: { main: '#ca8a04' },
      success: { main: '#059669' },
      background: isDark
        ? { default: '#0a0e1a', paper: '#111827' }
        : { default: '#f4f6f9', paper: '#ffffff' },
      text: isDark
        ? { primary: '#e8eaf6', secondary: '#8892a4' }
        : { primary: '#1a2332', secondary: '#5f6b7a' },
      divider: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
    },
    typography: sharedTypography(),
    shape: { borderRadius: tokens.cardRadius },
    components: sharedComponents(mode),
  });
}
