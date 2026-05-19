import React, { useState } from 'react';
import {
  Box, Drawer, List, ListItem, ListItemIcon,
  ListItemText, Typography, Avatar, Tooltip, Divider, Chip,
  useTheme,
} from '@mui/material';
import {
  Dashboard, Security, Block, Rule, Menu,
  Logout, ChevronLeft, Wifi, Settings as SettingsIcon, History, ListAlt,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import useCurrentUser from '../../hooks/useCurrentUser';
import { useLanguage } from '../../context/LanguageContext';
import NotificationBell from './NotificationBell';

const DRAWER_WIDTH = 240;
const DRAWER_MINI = 72;

function isNavActive(itemPath, pathname) {
  if (itemPath === '/incidents') {
    return pathname === '/incidents' || /^\/incidents\/\d+$/.test(pathname);
  }
  if (itemPath === '/incidents/all') {
    return pathname === '/incidents/all';
  }
  return pathname === itemPath || (itemPath !== '/' && pathname.startsWith(itemPath));
}

const NAV_ITEMS = [
  { labelKey: 'nav.dashboard', Icon: Dashboard, path: '/' },
  { labelKey: 'nav.incidents', Icon: Security, path: '/incidents' },
  { labelKey: 'nav.allIncidents', Icon: ListAlt, path: '/incidents/all' },
  { labelKey: 'nav.ipManagement', Icon: Block, path: '/blocked-ips' },
  { labelKey: 'nav.rules', Icon: Rule, path: '/rules' },
  { labelKey: 'nav.traffic', Icon: Wifi, path: '/traffic' },
  { labelKey: 'nav.settings', Icon: SettingsIcon, path: '/settings' },
];

export default function Layout({ children, onLogout }) {
  const [expanded, setExpanded] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const { t } = useLanguage();
  const drawerWidth = expanded ? DRAWER_WIDTH : DRAWER_MINI;
  const currentUser = useCurrentUser();
  const isAdmin = currentUser?.role === 'admin';
  const sem = theme.semantic;
  const sidebarBg = theme.palette.background.paper;

  const navItems = isAdmin
    ? [...NAV_ITEMS, { labelKey: 'nav.auditLog', Icon: History, path: '/audit' }]
    : NAV_ITEMS;

  const roleChipColor = currentUser?.role === 'admin'
    ? { color: sem.chipAdmin.color, bgcolor: sem.chipAdmin.bg, borderColor: sem.chipAdmin.borderColor }
    : { color: sem.chipAnalyst.color, bgcolor: sem.chipAnalyst.bg, borderColor: sem.chipAnalyst.borderColor };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            bgcolor: sidebarBg,
            overflow: 'hidden',
            transition: 'width 0.2s',
          },
        }}
      >
        <Box sx={{
          p: expanded ? 2 : 1.25,
          display: 'flex',
          flexDirection: expanded ? 'row' : 'column',
          alignItems: 'center',
          justifyContent: expanded ? 'space-between' : 'center',
          gap: expanded ? 1 : 0.75,
          minHeight: expanded ? 64 : 'auto',
        }}
        >
          <Box sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
            minWidth: 0,
            flex: expanded ? 1 : 'none',
            justifyContent: 'center',
          }}
          >
            <Box
              component="img"
              src="/icons/smeguard.png"
              alt="SME-Guard"
              sx={{
                width: expanded ? 36 : 32,
                height: expanded ? 36 : 32,
                borderRadius: 2,
                flexShrink: 0,
                objectFit: 'contain',
              }}
            />
            {expanded && (
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 800, color: 'primary.main', lineHeight: 1 }}>
                  SME-Guard
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                  Web SOC Platform
                </Typography>
              </Box>
            )}
          </Box>
          <NotificationBell compact={!expanded} />
        </Box>

        <Divider />

        <List sx={{ px: 1, pt: 1, flex: 1 }}>
          {navItems.map((item) => {
            const active = isNavActive(item.path, location.pathname);
            const Icon = item.Icon;
            return (
              <Tooltip key={item.path} title={!expanded ? t(item.labelKey) : ''} placement="right">
                <ListItem
                  button
                  onClick={() => navigate(item.path)}
                  sx={{
                    borderRadius: 2, mb: 0.5,
                    bgcolor: active ? sem.navActive.bg : 'transparent',
                    border: active ? `1px solid ${sem.navActive.border}` : '1px solid transparent',
                    '&:hover': { bgcolor: sem.navHover.bg },
                    px: expanded ? 2 : 1.5,
                    justifyContent: expanded ? 'flex-start' : 'center',
                  }}
                >
                  <ListItemIcon sx={{
                    color: active ? 'primary.main' : 'text.secondary',
                    minWidth: expanded ? 40 : 'auto',
                  }}>
                    <Icon />
                  </ListItemIcon>
                  {expanded && (
                    <ListItemText
                      primary={t(item.labelKey)}
                      primaryTypographyProps={{
                        fontWeight: active ? 700 : 500,
                        fontSize: '0.875rem',
                        color: active ? 'primary.main' : 'text.primary',
                      }}
                    />
                  )}
                </ListItem>
              </Tooltip>
            );
          })}
        </List>

        <Divider />

        {currentUser && expanded && (
          <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', color: 'primary.contrastText', fontSize: '0.9rem', fontWeight: 700, opacity: 0.9 }}>
              {currentUser.username?.[0]?.toUpperCase()}
            </Avatar>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2" noWrap sx={{ fontWeight: 600, fontSize: '0.82rem' }}>
                {currentUser.username}
              </Typography>
              <Chip
                label={currentUser.role}
                size="small"
                variant="outlined"
                sx={{ height: 18, fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', ...roleChipColor }}
              />
            </Box>
          </Box>
        )}

        <Box sx={{ p: 1 }}>
          <Tooltip title={expanded ? t('common.collapse') : t('common.expand')} placement="right">
            <ListItem
              button
              onClick={() => setExpanded(!expanded)}
              sx={{ borderRadius: 2, justifyContent: expanded ? 'flex-start' : 'center', px: expanded ? 2 : 1.5 }}
            >
              <ListItemIcon sx={{ color: 'text.secondary', minWidth: expanded ? 40 : 'auto' }}>
                {expanded ? <ChevronLeft /> : <Menu />}
              </ListItemIcon>
              {expanded && (
                <ListItemText
                  primary={t('common.collapse')}
                  primaryTypographyProps={{ fontSize: '0.8rem', color: 'text.secondary' }}
                />
              )}
            </ListItem>
          </Tooltip>
          <Tooltip title={t('common.logout')} placement="right">
            <ListItem
              button
              onClick={onLogout}
              sx={{ borderRadius: 2, justifyContent: expanded ? 'flex-start' : 'center', px: expanded ? 2 : 1.5 }}
            >
              <ListItemIcon sx={{ color: 'error.main', minWidth: expanded ? 40 : 'auto' }}>
                <Logout />
              </ListItemIcon>
              {expanded && (
                <ListItemText
                  primary={t('common.logout')}
                  primaryTypographyProps={{ fontSize: '0.8rem', color: 'error.main' }}
                />
              )}
            </ListItem>
          </Tooltip>
        </Box>
      </Drawer>

      <Box component="main" sx={{ flex: 1, p: 3, overflow: 'auto', minWidth: 0 }}>
        {children}
      </Box>
    </Box>
  );
}
