import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  IconButton, Badge, Menu, MenuItem, Typography, Box, Button, Divider, ListItemText,
} from '@mui/material';
import { Notifications, NotificationsNone } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { getNotificationsSummary } from '../../services/api';
import { useLanguage } from '../../context/LanguageContext';
import { formatLocaleDate } from '../../utils/locale';
import { SeverityChip, AttackTypeChip } from './Chips';
import { unlockNotificationSound, playNotificationSound } from '../../utils/notificationSound';

const POLL_MS = 30000;
const LAST_SEEN_KEY = 'sme_notif_last_seen_id';

function readLastSeenId() {
  const raw = localStorage.getItem(LAST_SEEN_KEY);
  const n = parseInt(raw, 10);
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

export default function NotificationBell({ compact = false }) {
  const navigate = useNavigate();
  const { t, language } = useLanguage();
  const [anchorEl, setAnchorEl] = useState(null);
  const [summary, setSummary] = useState({ unread_count: 0, max_new_id: 0, recent: [] });
  const [lastSeenId, setLastSeenId] = useState(readLastSeenId);
  const prevUnread = useRef(null);
  const token = typeof window !== 'undefined' ? localStorage.getItem('incidentra_token') : null;

  const fetchSummary = useCallback(async () => {
    if (!localStorage.getItem('incidentra_token')) return;
    try {
      const sinceId = readLastSeenId();
      const res = await getNotificationsSummary(sinceId);
      const data = res.data;
      setSummary(data);
      if (
        prevUnread.current !== null
        && data.unread_count > prevUnread.current
        && data.recent?.[0]
      ) {
        const latest = data.recent[0];
        toast.info(
          t('notifications.newAlert', { type: latest.attack_type, ip: latest.source_ip }),
          { autoClose: 2500, position: 'top-right' },
        );
        playNotificationSound();
      }
      prevUnread.current = data.unread_count;
    } catch {
      /* ignore poll errors */
    }
  }, [t]);

  useEffect(() => {
    if (!token) return undefined;
    fetchSummary();
    const id = setInterval(fetchSummary, POLL_MS);
    return () => clearInterval(id);
  }, [token, fetchSummary]);

  const handleMarkAllRead = () => {
    const next = summary.max_new_id || 0;
    localStorage.setItem(LAST_SEEN_KEY, String(next));
    setLastSeenId(next);
    prevUnread.current = 0;
    setSummary((s) => ({ ...s, unread_count: 0 }));
    fetchSummary();
  };

  const open = Boolean(anchorEl);
  const unread = summary.unread_count ?? 0;
  const BellIcon = unread > 0 ? Notifications : NotificationsNone;

  if (!token) return null;

  return (
    <>
      <IconButton
        size={compact ? 'small' : 'medium'}
        onClick={(e) => {
          unlockNotificationSound();
          setAnchorEl(e.currentTarget);
        }}
        aria-label={t('notifications.title')}
        sx={{
          color: unread > 0 ? 'primary.main' : 'text.secondary',
          flexShrink: 0,
          bgcolor: unread > 0 ? 'action.hover' : 'transparent',
          '&:hover': { bgcolor: 'action.selected' },
        }}
      >
        <Badge badgeContent={unread > 0 ? unread : null} color="error" max={99}>
          <BellIcon fontSize={compact ? 'small' : 'medium'} />
        </Badge>
      </IconButton>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        slotProps={{
          paper: {
            sx: {
              width: 340,
              maxHeight: 400,
              ml: 1,
            },
          },
        }}
      >
        <Box sx={{
          px: 2, py: 1.25,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            {t('notifications.title')}
          </Typography>
          {unread > 0 && (
            <Button size="small" onClick={handleMarkAllRead} sx={{ minWidth: 0, fontSize: '0.75rem' }}>
              {t('notifications.markAllRead')}
            </Button>
          )}
        </Box>
        <Divider />

        {summary.recent?.length === 0 ? (
          <Box sx={{ px: 2, py: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              {t('notifications.empty')}
            </Typography>
          </Box>
        ) : (
          summary.recent.map((item) => (
            <MenuItem
              key={item.id}
              onClick={() => {
                setAnchorEl(null);
                navigate(`/incidents/${item.id}`);
              }}
              sx={{
                alignItems: 'flex-start',
                py: 1.25,
                opacity: item.id > lastSeenId ? 1 : 0.7,
                borderLeft: item.id > lastSeenId ? '3px solid' : '3px solid transparent',
                borderColor: item.id > lastSeenId ? 'primary.main' : 'transparent',
              }}
            >
              <ListItemText
                primary={(
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap' }}>
                    <AttackTypeChip type={item.attack_type} />
                    <SeverityChip severity={item.severity} />
                  </Box>
                )}
                secondary={(
                  <>
                    <Typography component="span" variant="body2" sx={{ fontFamily: 'monospace', display: 'block' }}>
                      {item.source_ip}
                    </Typography>
                    <Typography component="span" variant="caption" color="text.secondary">
                      {formatLocaleDate(item.created_at, language, {
                        month: 'short', day: 'numeric',
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </Typography>
                  </>
                )}
              />
            </MenuItem>
          ))
        )}

        <Divider sx={{ mt: 0.5 }} />
        <MenuItem
          onClick={() => {
            setAnchorEl(null);
            navigate('/incidents');
          }}
          sx={{ justifyContent: 'center', py: 1.25 }}
        >
          <Typography variant="body2" color="primary.main" sx={{ fontWeight: 600 }}>
            {t('notifications.viewOngoing')}
          </Typography>
        </MenuItem>
      </Menu>
    </>
  );
}
