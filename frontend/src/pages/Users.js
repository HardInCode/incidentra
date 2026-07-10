// Admin User Management: approve pending registrations, assign roles, suspend, reset password.
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box, Card, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Button, TextField, Dialog,
  DialogTitle, DialogContent, DialogActions, IconButton, Tooltip,
  CircularProgress, Select, MenuItem, FormControl, InputLabel, Alert,
} from '@mui/material';
import { People, Add, Delete, Refresh, CheckCircle, Block, LockReset, ContentCopy } from '@mui/icons-material';
import { Navigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  listUsers, createUser, updateUser, resetUserPassword, deleteUser,
} from '../services/api';
import FilterBar from '../components/shared/FilterBar';
import { AccountStatusChip } from '../components/shared/Chips';
import useCurrentUser from '../hooks/useCurrentUser';
import { useLanguage } from '../context/LanguageContext';
import { formatLocaleDate } from '../utils/locale';

const dialogContentSx = {
  display: 'flex',
  flexDirection: 'column',
  gap: 2.5,
  pt: 3,
  pb: 1,
  overflow: 'visible',
};

const tableHeadCellSx = {
  whiteSpace: 'nowrap',
  fontWeight: 700,
  py: 1.5,
};

export default function Users() {
  const { t, language } = useLanguage();
  const currentUser = useCurrentUser();
  const isAdmin = currentUser?.role === 'admin';

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({ username: '', email: '', password: '', role: 'analyst' });

  const [manageOpen, setManageOpen] = useState(false);
  const [managingUser, setManagingUser] = useState(null);
  const [manageForm, setManageForm] = useState({ role: 'analyst', status: 'active' });

  const [resetOpen, setResetOpen] = useState(false);
  const [resettingUser, setResettingUser] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [generatedPassword, setGeneratedPassword] = useState('');

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletingUser, setDeletingUser] = useState(null);

  const FILTER_CONFIG = useMemo(() => [
    {
      key: 'status',
      label: t('users.filterStatus'),
      options: [
        { value: 'pending', label: t('accountStatus.pending') },
        { value: 'active', label: t('accountStatus.active') },
        { value: 'suspended', label: t('accountStatus.suspended') },
      ],
    },
  ], [t]);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (search) params.search = search;
      const res = await listUsers(params);
      setUsers(res.data);
    } catch {
      toast.error(t('users.actionFailed'));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search, t]);

  useEffect(() => { if (isAdmin) fetchUsers(); }, [fetchUsers, isAdmin]);

  if (!isAdmin) {
    return <Navigate to="/settings" replace />;
  }

  const formatDate = (iso) => formatLocaleDate(iso, language);

  const handleClearFilters = () => {
    setStatusFilter('');
    setSearch('');
  };

  const handleCreate = async () => {
    try {
      await createUser(createForm);
      toast.success(t('users.createSuccess', { username: createForm.username }));
      setCreateOpen(false);
      setCreateForm({ username: '', email: '', password: '', role: 'analyst' });
      fetchUsers();
    } catch (e) {
      toast.error(e.response?.data?.error || t('users.createFailed'));
    }
  };

  const openManage = (user) => {
    setManagingUser(user);
    setManageForm({ role: user.role || 'analyst', status: user.status });
    setManageOpen(true);
  };

  const handleManageSave = async () => {
    if (!managingUser) return;
    try {
      const res = await updateUser(managingUser.id, manageForm);
      const wasApprove = managingUser.status === 'pending' && manageForm.status === 'active';
      toast.success(t(wasApprove ? 'users.approveSuccess' : 'users.updateSuccess', { username: res.data.username }));
      setManageOpen(false);
      setManagingUser(null);
      fetchUsers();
    } catch (e) {
      toast.error(e.response?.data?.error || t('users.actionFailed'));
    }
  };

  const handleQuickStatus = async (user, status) => {
    try {
      const res = await updateUser(user.id, { status });
      const key = status === 'suspended' ? 'users.suspendSuccess' : 'users.reactivateSuccess';
      toast.success(t(key, { username: res.data.username }));
      fetchUsers();
    } catch (e) {
      toast.error(e.response?.data?.error || t('users.actionFailed'));
    }
  };

  const openReset = (user) => {
    setResettingUser(user);
    setNewPassword('');
    setGeneratedPassword('');
    setResetOpen(true);
  };

  const handleReset = async () => {
    if (!resettingUser) return;
    try {
      const res = await resetUserPassword(resettingUser.id, newPassword ? { new_password: newPassword } : {});
      toast.success(t('users.resetPasswordSuccess', { username: resettingUser.username }));
      if (res.data.generated_password) {
        setGeneratedPassword(res.data.generated_password);
      } else {
        setResetOpen(false);
        setResettingUser(null);
      }
    } catch (e) {
      toast.error(e.response?.data?.error || t('users.resetPasswordFailed'));
    }
  };

  const handleCopyPassword = () => {
    navigator.clipboard?.writeText(generatedPassword);
    toast.success(t('users.copied'));
  };

  const openDelete = (user) => {
    setDeletingUser(user);
    setDeleteOpen(true);
  };

  const handleDelete = async () => {
    if (!deletingUser) return;
    try {
      await deleteUser(deletingUser.id);
      toast.success(t('users.deleteSuccess', { username: deletingUser.username }));
      setDeleteOpen(false);
      setDeletingUser(null);
      fetchUsers();
    } catch (e) {
      toast.error(e.response?.data?.error || t('users.deleteFailed'));
    }
  };

  const hasActiveFilters = !!(statusFilter || search);
  const isSelf = (user) => user.id === currentUser?.user_id;

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <People sx={{ fontSize: 28, color: 'primary.main' }} />
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800 }}>{t('users.title')}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              {t('users.subtitle', { count: users.length })}
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" startIcon={<Add />} onClick={() => setCreateOpen(true)}>
            {t('users.addUser')}
          </Button>
          <IconButton onClick={fetchUsers} sx={{ color: 'primary.main' }}><Refresh /></IconButton>
        </Box>
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>{t('users.info')}</Alert>

      <FilterBar
        filters={FILTER_CONFIG}
        values={{ status: statusFilter }}
        onChange={(_, val) => setStatusFilter(val)}
        searchValue={search}
        searchPlaceholder={t('users.searchPlaceholder')}
        onSearch={setSearch}
        hasActiveFilters={hasActiveFilters}
        onClear={handleClearFilters}
      />

      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={tableHeadCellSx}>{t('users.colUsername')}</TableCell>
                <TableCell sx={tableHeadCellSx}>{t('users.colEmail')}</TableCell>
                <TableCell sx={tableHeadCellSx}>{t('users.colRole')}</TableCell>
                <TableCell sx={tableHeadCellSx}>{t('users.colStatus')}</TableCell>
                <TableCell sx={tableHeadCellSx}>{t('users.colCreatedAt')}</TableCell>
                <TableCell align="center" sx={tableHeadCellSx}>{t('common.actions')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={6} align="center" sx={{ py: 6 }}><CircularProgress size={28} /></TableCell></TableRow>
              ) : users.length === 0 ? (
                <TableRow><TableCell colSpan={6} align="center" sx={{ py: 6, color: 'text.secondary' }}>{t('users.empty')}</TableCell></TableRow>
              ) : users.map((user) => (
                <TableRow key={user.id} hover>
                  <TableCell sx={{ fontWeight: 600 }}>{user.username}</TableCell>
                  <TableCell sx={{ fontSize: '0.85rem', color: 'text.secondary' }}>{user.email}</TableCell>
                  <TableCell sx={{ fontSize: '0.85rem' }}>{user.role || t('users.noRole')}</TableCell>
                  <TableCell><AccountStatusChip status={user.status} /></TableCell>
                  <TableCell sx={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>{formatDate(user.created_at)}</TableCell>
                  <TableCell align="center" sx={{ whiteSpace: 'nowrap' }}>
                    {user.status === 'pending' && (
                      <Tooltip title={t('users.approve')}>
                        <IconButton size="small" onClick={() => openManage(user)} sx={{ color: '#00a884', mr: 0.5 }}>
                          <CheckCircle sx={{ fontSize: 18 }} />
                        </IconButton>
                      </Tooltip>
                    )}
                    {user.status !== 'pending' && (
                      <Tooltip title={isSelf(user) ? t('users.cannotModifySelf') : (user.status === 'suspended' ? t('users.reactivate') : t('users.suspend'))}>
                        <span>
                          <IconButton
                            size="small"
                            disabled={isSelf(user)}
                            onClick={() => (user.status === 'suspended' ? handleQuickStatus(user, 'active') : handleQuickStatus(user, 'suspended'))}
                            sx={{ color: user.status === 'suspended' ? '#00a884' : '#ff9800', mr: 0.5 }}
                          >
                            {user.status === 'suspended' ? <CheckCircle sx={{ fontSize: 18 }} /> : <Block sx={{ fontSize: 18 }} />}
                          </IconButton>
                        </span>
                      </Tooltip>
                    )}
                    <Tooltip title={t('users.manageTitle')}>
                      <IconButton size="small" onClick={() => openManage(user)} sx={{ color: 'primary.main', mr: 0.5 }}>
                        <People sx={{ fontSize: 18 }} />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={t('users.resetPassword')}>
                      <IconButton size="small" onClick={() => openReset(user)} sx={{ color: '#7c4dff', mr: 0.5 }}>
                        <LockReset sx={{ fontSize: 18 }} />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={isSelf(user) ? t('users.cannotModifySelf') : t('users.delete')}>
                      <span>
                        <IconButton size="small" disabled={isSelf(user)} onClick={() => openDelete(user)} sx={{ color: '#ff4444' }}>
                          <Delete sx={{ fontSize: 18 }} />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Create user */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ pb: 1 }}>{t('users.createTitle')}</DialogTitle>
        <DialogContent sx={dialogContentSx}>
          <TextField
            fullWidth label={t('users.createUsername')}
            value={createForm.username}
            onChange={(e) => setCreateForm((f) => ({ ...f, username: e.target.value }))}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            fullWidth label={t('users.createEmail')}
            value={createForm.email}
            onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            fullWidth label={t('users.createPassword')}
            type="password"
            value={createForm.password}
            onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
            InputLabelProps={{ shrink: true }}
          />
          <FormControl fullWidth size="small">
            <InputLabel id="create-role-label" shrink>{t('users.createRole')}</InputLabel>
            <Select
              labelId="create-role-label"
              value={createForm.role}
              label={t('users.createRole')}
              onChange={(e) => setCreateForm((f) => ({ ...f, role: e.target.value }))}
            >
              <MenuItem value="analyst">analyst</MenuItem>
              <MenuItem value="admin">admin</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>{t('common.cancel')}</Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={!createForm.username || !createForm.email || !createForm.password}
          >
            {t('users.addUser')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Manage role/status */}
      <Dialog open={manageOpen} onClose={() => setManageOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ pb: 1 }}>{t('users.manageTitle')} — {managingUser?.username}</DialogTitle>
        <DialogContent sx={dialogContentSx}>
          <FormControl fullWidth size="small">
            <InputLabel id="manage-role-label" shrink>{t('users.manageRoleLabel')}</InputLabel>
            <Select
              labelId="manage-role-label"
              value={manageForm.role}
              label={t('users.manageRoleLabel')}
              onChange={(e) => setManageForm((f) => ({ ...f, role: e.target.value }))}
            >
              <MenuItem value="analyst">analyst</MenuItem>
              <MenuItem value="admin">admin</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth size="small">
            <InputLabel id="manage-status-label" shrink>{t('users.manageStatusLabel')}</InputLabel>
            <Select
              labelId="manage-status-label"
              value={manageForm.status}
              label={t('users.manageStatusLabel')}
              onChange={(e) => setManageForm((f) => ({ ...f, status: e.target.value }))}
            >
              <MenuItem value="pending">{t('accountStatus.pending')}</MenuItem>
              <MenuItem value="active">{t('accountStatus.active')}</MenuItem>
              <MenuItem value="suspended">{t('accountStatus.suspended')}</MenuItem>
            </Select>
          </FormControl>
          <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.5 }}>{t('users.manageHint')}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setManageOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleManageSave}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>

      {/* Reset password */}
      <Dialog open={resetOpen} onClose={() => { setResetOpen(false); setGeneratedPassword(''); }} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ pb: 1 }}>{t('users.resetPasswordTitle', { username: resettingUser?.username })}</DialogTitle>
        <DialogContent sx={dialogContentSx}>
          {generatedPassword ? (
            <Alert severity="success" sx={{ wordBreak: 'break-all' }}>
              <Typography variant="caption" sx={{ display: 'block', mb: 0.5 }}>
                {t('users.generatedPasswordLabel')}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography component="code" sx={{ fontFamily: 'monospace', fontWeight: 700 }}>
                  {generatedPassword}
                </Typography>
                <Tooltip title={t('users.copy')}>
                  <IconButton size="small" onClick={handleCopyPassword}><ContentCopy sx={{ fontSize: 16 }} /></IconButton>
                </Tooltip>
              </Box>
            </Alert>
          ) : (
            <>
              <TextField
                fullWidth
                label={t('users.newPasswordLabel')}
                type="text"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                InputLabelProps={{ shrink: true }}
              />
              <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1.5 }}>
                {t('users.resetPasswordHint')}
              </Typography>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setResetOpen(false); setGeneratedPassword(''); }}>
            {generatedPassword ? t('common.save') : t('common.cancel')}
          </Button>
          {!generatedPassword && (
            <Button variant="contained" onClick={handleReset}>{t('users.resetPasswordButton')}</Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Delete confirm */}
      <Dialog open={deleteOpen} onClose={() => setDeleteOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ pb: 1 }}>{t('users.deleteTitle')}</DialogTitle>
        <DialogContent sx={dialogContentSx}>
          <Typography variant="body2">
            {t('users.deleteConfirm', { username: deletingUser?.username })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>{t('users.delete')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
