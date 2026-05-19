import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Card, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TablePagination, TextField,
  CircularProgress, Alert,
} from '@mui/material';
import { History } from '@mui/icons-material';
import { Navigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { getAuditLogs } from '../services/api';
import useCurrentUser from '../hooks/useCurrentUser';
import { useLanguage } from '../context/LanguageContext';
import { formatLocaleDate } from '../utils/locale';

export default function AuditLog() {
  const { t, language } = useLanguage();
  const currentUser = useCurrentUser();
  const isAdmin = currentUser?.role === 'admin';

  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(25);
  const [loading, setLoading] = useState(false);
  const [userFilter, setUserFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getAuditLogs({
        page: page + 1,
        per_page: perPage,
        user: userFilter || undefined,
        action: actionFilter || undefined,
      });
      setLogs(res.data.logs);
      setTotal(res.data.total);
    } catch {
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, [page, perPage, userFilter, actionFilter]);

  useEffect(() => { if (isAdmin) fetchLogs(); }, [fetchLogs, isAdmin]);

  if (!isAdmin) {
    return <Navigate to="/settings" replace />;
  }

  const formatDate = (iso) => formatLocaleDate(iso, language);

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
        <History sx={{ fontSize: 28, color: 'primary.main' }} />
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>{t('audit.title')}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t('audit.subtitle')}
          </Typography>
        </Box>
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>
        {t('audit.info')}
      </Alert>

      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <TextField
          size="small"
          label={t('audit.user')}
          value={userFilter}
          onChange={(e) => { setUserFilter(e.target.value); setPage(0); }}
          sx={{ minWidth: 160 }}
        />
        <TextField
          size="small"
          label={t('audit.action')}
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(0); }}
          placeholder={t('audit.actionPlaceholder')}
          sx={{ minWidth: 200 }}
        />
      </Box>

      <Card>
        <TableContainer>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>{t('audit.colTime')}</TableCell>
                <TableCell>{t('audit.colUser')}</TableCell>
                <TableCell>{t('audit.colAction')}</TableCell>
                <TableCell>{t('audit.colResource')}</TableCell>
                <TableCell>{t('audit.colDetails')}</TableCell>
                <TableCell>{t('audit.colIp')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <CircularProgress size={28} />
                  </TableCell>
                </TableRow>
              ) : logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                    {t('audit.empty')}
                  </TableCell>
                </TableRow>
              ) : logs.map((log) => (
                <TableRow key={log.id} hover>
                  <TableCell sx={{ whiteSpace: 'nowrap', fontSize: '0.8rem' }}>{formatDate(log.created_at)}</TableCell>
                  <TableCell>{log.user}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{log.action}</TableCell>
                  <TableCell sx={{ fontSize: '0.85rem' }}>{log.resource}</TableCell>
                  <TableCell sx={{ fontSize: '0.75rem', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {log.details}
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{log.ip_address || '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          count={total}
          page={page}
          rowsPerPage={perPage}
          onPageChange={(e, p) => setPage(p)}
          onRowsPerPageChange={(e) => { setPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          labelRowsPerPage={t('common.rowsPerPage')}
        />
      </Card>
    </Box>
  );
}
