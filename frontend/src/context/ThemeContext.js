import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { ThemeProvider as MuiThemeProvider } from '@mui/material';
import {
  createAppTheme,
  getInitialMode,
  resolveMode,
  THEME_STORAGE_KEY,
} from '../theme';

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [preference, setPreference] = useState(() => {
    try {
      return localStorage.getItem(THEME_STORAGE_KEY) || 'dark';
    } catch {
      return 'dark';
    }
  });
  const [resolvedMode, setResolvedMode] = useState(getInitialMode);

  useEffect(() => {
    const mode = resolveMode(preference);
    setResolvedMode(mode);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, preference);
    } catch {
      /* ignore */
    }
    document.documentElement.setAttribute('data-theme', mode);
    document.body.style.backgroundColor = mode === 'dark' ? '#0a0e1a' : '#f4f6f9';
  }, [preference]);

  useEffect(() => {
    if (preference !== 'system') return undefined;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => setResolvedMode(resolveMode('system'));
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [preference]);

  const theme = useMemo(() => createAppTheme(resolvedMode), [resolvedMode]);

  const value = useMemo(
    () => ({
      preference,
      mode: resolvedMode,
      setPreference,
    }),
    [preference, resolvedMode],
  );

  return (
    <ThemeContext.Provider value={value}>
      <MuiThemeProvider theme={theme}>{children}</MuiThemeProvider>
    </ThemeContext.Provider>
  );
}

export function useThemeMode() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useThemeMode must be used within ThemeProvider');
  return ctx;
}
