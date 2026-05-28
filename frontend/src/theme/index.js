import { createTheme } from '@mui/material';

export const THEME_STORAGE_KEY = 'incidentra-theme';

export const severityColors = {
  critical: '#ff1744',
  high: '#ff6d00',
  medium: '#ffd600',
  low: '#00e676',
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
      bg: isDark ? 'rgba(0,230,118,0.12)' : 'rgba(0,168,132,0.14)',
      border: isDark ? 'rgba(0,230,118,0.35)' : 'rgba(0,168,132,0.45)',
      color: isDark ? '#00e676' : '#007a5e',
    },
    alertWarning: {
      bg: isDark ? 'rgba(255,214,0,0.12)' : 'rgba(255,193,7,0.18)',
      border: isDark ? 'rgba(255,214,0,0.35)' : 'rgba(230,162,0,0.45)',
      color: isDark ? '#ffd600' : '#b45309',
    },
    alertError: {
      bg: isDark ? 'rgba(255,23,68,0.12)' : 'rgba(244,67,54,0.12)',
      border: isDark ? 'rgba(255,23,68,0.35)' : 'rgba(211,47,47,0.4)',
      color: isDark ? '#ff1744' : '#c62828',
    },
    chipBlocked: {
      bg: isDark ? 'rgba(255,23,68,0.15)' : 'rgba(244,67,54,0.12)',
      color: isDark ? '#ff1744' : '#c62828',
      border: isDark ? 'rgba(255,23,68,0.4)' : 'rgba(211,47,47,0.35)',
    },
    chipTemporary: {
      bg: isDark ? 'rgba(255,214,0,0.12)' : 'rgba(255,193,7,0.18)',
      color: isDark ? '#ffd600' : '#b45309',
      border: isDark ? 'rgba(255,214,0,0.35)' : 'rgba(230,162,0,0.4)',
    },
    chipExpired: {
      bg: isDark ? 'rgba(136,146,164,0.15)' : 'rgba(158,158,158,0.2)',
      color: isDark ? '#8892a4' : '#616161',
    },
    chipIncident: {
      bg: isDark ? 'rgba(255,109,0,0.12)' : 'rgba(255,109,0,0.14)',
      color: isDark ? '#ff6d00' : '#e65100',
    },
    navActive: {
      bg: isDark ? 'rgba(0,212,170,0.12)' : 'rgba(0,168,132,0.1)',
      border: isDark ? 'rgba(0,212,170,0.25)' : 'rgba(0,168,132,0.35)',
    },
    navHover: {
      bg: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
    },
    chipAdmin: {
      color: '#ff6d00',
      bg: isDark ? 'rgba(255,109,0,0.15)' : 'rgba(255,109,0,0.12)',
      borderColor: isDark ? 'rgba(255,109,0,0.3)' : 'rgba(255,109,0,0.35)',
    },
    chipAnalyst: {
      color: isDark ? '#00d4aa' : '#00a884',
      bg: isDark ? 'rgba(0,212,170,0.1)' : 'rgba(0,168,132,0.1)',
      borderColor: isDark ? 'rgba(0,212,170,0.25)' : 'rgba(0,168,132,0.3)',
    },
    severity: {
      critical: { color: '#ff1744', bg: isDark ? 'rgba(255,23,68,0.15)' : 'rgba(244,67,54,0.12)', border: isDark ? 'rgba(255,23,68,0.4)' : 'rgba(211,47,47,0.35)' },
      high:     { color: '#ff6d00', bg: isDark ? 'rgba(255,109,0,0.15)' : 'rgba(255,109,0,0.12)', border: isDark ? 'rgba(255,109,0,0.4)' : 'rgba(230,81,0,0.35)' },
      medium:   { color: isDark ? '#ffd600' : '#f57f17', bg: isDark ? 'rgba(255,214,0,0.12)' : 'rgba(255,193,7,0.15)', border: isDark ? 'rgba(255,214,0,0.35)' : 'rgba(230,162,0,0.35)' },
      low:      { color: isDark ? '#00e676' : '#007a5e', bg: isDark ? 'rgba(0,230,118,0.12)' : 'rgba(0,168,132,0.12)', border: isDark ? 'rgba(0,230,118,0.35)' : 'rgba(0,168,132,0.35)' },
    },
    status: {
      new:            { color: '#7c4dff', bg: isDark ? 'rgba(124,77,255,0.15)' : 'rgba(124,77,255,0.12)' },
      investigating:  { color: '#00b0ff', bg: isDark ? 'rgba(0,176,255,0.15)' : 'rgba(3,169,244,0.12)' },
      resolved:       { color: isDark ? '#00e676' : '#007a5e', bg: isDark ? 'rgba(0,230,118,0.12)' : 'rgba(0,168,132,0.12)' },
      false_positive: { color: isDark ? '#8892a4' : '#5f6b7a', bg: isDark ? 'rgba(136,146,164,0.12)' : 'rgba(158,158,158,0.15)' },
    },
    attackType: {
      color: isDark ? '#00d4aa' : '#00a884',
      border: isDark ? 'rgba(0,212,170,0.3)' : 'rgba(0,168,132,0.35)',
    },
    surfaceMuted: {
      bg: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)',
      border: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)',
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
        main: isDark ? '#00d4aa' : '#00a884',
        contrastText: isDark ? '#0a0e1a' : '#ffffff',
      },
      secondary: { main: '#7c4dff' },
      error: { main: '#ff4444' },
      warning: { main: '#ffaa00' },
      success: { main: '#00e676' },
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
