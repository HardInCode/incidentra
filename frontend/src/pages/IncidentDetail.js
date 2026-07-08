import React, { useState, useEffect } from 'react';
import {
  Box, Card, CardContent, Typography, Button, Grid, Divider,
  TextField, CircularProgress, Chip, Alert, Accordion, AccordionSummary,
  AccordionDetails, IconButton, Tooltip, Select, MenuItem, FormControl,
} from '@mui/material';
import {
  ArrowBack, AutoAwesome, Add, ExpandMore, Shield, ContentCopy, SmartToy,
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { getIncident, updateIncidentStatus, addIncidentNote, triggerExplanation, assignIncident, getUsers } from '../services/api';
import { getFlagEmoji } from '../utils/country';
import useCurrentUser from '../hooks/useCurrentUser';
import { useLanguage } from '../context/LanguageContext';
import { formatLocaleDate } from '../utils/locale';
import { SeverityChip, StatusChip, AttackTypeChip } from '../components/shared/Chips';
import { useChatbotContext } from '../context/ChatbotContext';

function InfoRow({ label, value, mono = false }) {
  return (
    <Box sx={{ display: 'flex', gap: 2, py: 1, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
      <Typography sx={{ color: 'text.secondary', fontSize: '0.8rem', minWidth: 140, flexShrink: 0, pt: 0.1 }}>
        {label}
      </Typography>
      <Typography sx={{ fontSize: '0.875rem', fontFamily: mono ? 'monospace' : 'inherit', wordBreak: 'break-all', color: mono ? '#00d4aa' : 'text.primary' }}>
        {value || '—'}
      </Typography>
    </Box>
  );
}

function AIExplanationCard({ explanation, onGenerate, generating }) {
  const { t } = useLanguage();
  if (!explanation) {
    return (
      <Card sx={{ border: '1px solid rgba(124,77,255,0.3)', background: 'rgba(124,77,255,0.05)' }}>
        <CardContent sx={{ textAlign: 'center', py: 4 }}>
          <AutoAwesome sx={{ fontSize: 40, color: '#7c4dff', mb: 2 }} />
          <Typography variant="h6" sx={{ mb: 1 }}>{t('incidentDetail.aiNotGenerated')}</Typography>
          <Typography variant="body2" sx={{ color: 'text.secondary', mb: 3 }}>
            {t('incidentDetail.aiHint')}
          </Typography>
          <Button
            variant="contained"
            startIcon={generating ? <CircularProgress size={16} color="inherit" /> : <AutoAwesome />}
            onClick={onGenerate}
            disabled={generating}
            color="primary"
          >
            {generating ? t('incidentDetail.generating') : t('incidentDetail.generate')}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card sx={{ border: '1px solid rgba(0,212,170,0.25)', background: 'rgba(0,212,170,0.04)' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <AutoAwesome sx={{ color: '#7c4dff' }} />
          <Typography variant="h6">{t('incidentDetail.aiTitle')}</Typography>
          <Tooltip title={t('incidentDetail.modelTooltip', { model: explanation.model_used })}>
            <Chip
              label={explanation.model_used}
              size="small"
              sx={{ ml: 'auto', color: 'text.secondary', fontSize: '0.7rem', maxWidth: 220 }}
            />
          </Tooltip>
        </Box>

        <Box sx={{ mb: 2, p: 2, bgcolor: 'rgba(0,0,0,0.3)', borderRadius: 2, borderLeft: '3px solid #00d4aa' }}>
          <Typography variant="body2" sx={{ color: '#00d4aa', fontWeight: 600, mb: 0.5, fontSize: '0.75rem', textTransform: 'uppercase' }}>
            {t('incidentDetail.summary')}
          </Typography>
          <Typography variant="body1">{explanation.ai_summary}</Typography>
        </Box>

        {explanation.threat_explanation && (
          <Box sx={{ mb: 2, p: 2, bgcolor: 'rgba(0,0,0,0.3)', borderRadius: 2, borderLeft: '3px solid #ff6d00' }}>
            <Typography variant="body2" sx={{ color: '#ff6d00', fontWeight: 600, mb: 0.5, fontSize: '0.75rem', textTransform: 'uppercase' }}>
              {t('incidentDetail.whyDangerous')}
            </Typography>
            <Typography variant="body2">{explanation.threat_explanation}</Typography>
          </Box>
        )}

        {explanation.recommended_actions && (
          <Box sx={{ mb: 2, p: 2, bgcolor: 'rgba(0,0,0,0.3)', borderRadius: 2, borderLeft: '3px solid #7c4dff' }}>
            <Typography variant="body2" sx={{ color: '#7c4dff', fontWeight: 600, mb: 1, fontSize: '0.75rem', textTransform: 'uppercase' }}>
              {t('incidentDetail.recommended')}
            </Typography>
            {explanation.recommended_actions.split('\n').filter(Boolean).map((line, i) => (
              <Typography key={i} variant="body2" sx={{ mb: 0.5 }}>
                {line}
              </Typography>
            ))}
          </Box>
        )}

        {explanation.mitre_technique && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Shield sx={{ fontSize: 16, color: '#8892a4' }} />
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {t('incidentDetail.mitre')} <span style={{ color: '#00d4aa', fontFamily: 'monospace' }}>{explanation.mitre_technique}</span>
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

export default function IncidentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { t, language } = useLanguage();
  const [incident, setIncident] = useState(null);
  const [loading, setLoading] = useState(true);
  const [newNote, setNewNote] = useState('');
  const [generating, setGenerating] = useState(false);
  const [savingNote, setSavingNote] = useState(false);
  const [users, setUsers] = useState([]);
  const currentUser = useCurrentUser();
  const { setIncidentContext } = useChatbotContext();

  useEffect(() => {
    setIncidentContext(incident);
    return () => setIncidentContext(null);
  }, [incident, setIncidentContext]);

  useEffect(() => {
    if (currentUser?.role === 'admin' || currentUser?.role === 'analyst') {
      getUsers().then((res) => setUsers(res.data)).catch(() => {});
    }
  }, [currentUser?.role]);

  const fetchIncident = async () => {
    try {
      const res = await getIncident(id);
      setIncident(res.data);
    } catch (e) {
      toast.error('Failed to load incident');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchIncident(); }, [id]);

  const handleStatusChange = async (newStatus) => {
    try {
      await updateIncidentStatus(id, newStatus);
      toast.success('Status updated');
      fetchIncident();
    } catch (e) {
      toast.error('Failed to update status');
    }
  };

  const handleAddNote = async () => {
    if (!newNote.trim()) return;
    setSavingNote(true);
    try {
      await addIncidentNote(id, newNote);
      toast.success('Note added');
      setNewNote('');
      fetchIncident();
    } catch (e) {
      toast.error('Failed to add note');
    } finally {
      setSavingNote(false);
    }
  };

  const handleGenerateExplanation = async () => {
    setGenerating(true);
    try {
      const res = await triggerExplanation(id, language);
      if (res.data?.explanation) {
        toast.success('AI explanation generated!');
        fetchIncident();
      } else {
        toast.info('Explanation generated — refreshing…');
        fetchIncident();
      }
    } catch (e) {
      toast.error('Failed to generate explanation. Check GROQ_API_KEY in backend/.env');
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.info('Copied to clipboard');
  };

  const handleAssign = async (userId) => {
    try {
      await assignIncident(id, userId || null);
      toast.success('Analyst assigned');
      fetchIncident();
    } catch {
      toast.error('Failed to assign analyst');
    }
  };

  const getAbuseColor = (score) => {
    if (score >= 75) return { bg: 'rgba(255,68,68,0.15)', color: '#ff4444', border: '#ff444433' };
    if (score >= 25) return { bg: 'rgba(255,170,0,0.15)', color: '#ffaa00', border: '#ffaa0033' };
    return { bg: 'rgba(0,212,170,0.15)', color: '#00d4aa', border: '#00d4aa33' };
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 10 }}><CircularProgress /></Box>;
  if (!incident) return null;

  const formatDate = (iso) => formatLocaleDate(iso, language, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <IconButton onClick={() => navigate('/incidents')} sx={{ color: 'text.secondary' }}>
          <ArrowBack />
        </IconButton>
        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
            <Typography variant="h5" sx={{ fontWeight: 800 }}>{t('incidentDetail.title', { id: incident.id })}</Typography>
            <SeverityChip severity={incident.severity} />
            <AttackTypeChip type={incident.attack_type} />
          </Box>
          <Typography variant="body2" sx={{ color: 'text.secondary', mt: 0.3 }}>
            {t('incidentDetail.detected', { date: formatDate(incident.created_at) })}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <StatusChip status={incident.status} />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <Select
              value={incident.status}
              onChange={e => handleStatusChange(e.target.value)}
              displayEmpty
            >
              {['new', 'investigating', 'resolved', 'false_positive'].map(s => (
                <MenuItem key={s} value={s}>{t(`status.${s}`)}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Box>

      <Grid container spacing={2}>
        {/* Left: Details */}
        <Grid item xs={12} md={6}>
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>{t('incidentDetail.details')}</Typography>
              <InfoRow label={t('incidentDetail.sourceIp')} value={incident.source_ip} mono />
              <InfoRow label={t('incidentDetail.attackType')} value={incident.attack_type?.replace(/_/g, ' ')} />
              <InfoRow label={t('incidentDetail.severity')} value={t(`severity.${incident.severity}`)} />
              <InfoRow label={t('incidentDetail.requestMethod')} value={incident.request_method} mono />
              <InfoRow label={t('incidentDetail.requestPath')} value={incident.request_path} mono />
              <InfoRow label={t('incidentDetail.httpStatus')} value={incident.response_code} />
              {incident.country_code && (
                <InfoRow
                  label={t('incidentDetail.country')}
                  value={`${getFlagEmoji(incident.country_code)} ${incident.country_code}`}
                />
              )}
              {incident.abuse_confidence_score != null && (() => {
                const c = getAbuseColor(incident.abuse_confidence_score);
                return (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 1, borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                    <Typography variant="body2" color="text.secondary">{t('incidentDetail.abuseScore')}</Typography>
                    <Chip
                      label={t('incidentDetail.abuseConfidence', { score: incident.abuse_confidence_score })}
                      size="small"
                      sx={{ fontWeight: 700, bgcolor: c.bg, color: c.color, border: `1px solid ${c.border}` }}
                    />
                  </Box>
                );
              })()}
              <InfoRow label={t('incidentDetail.detectedAt')} value={formatDate(incident.created_at)} />
              <InfoRow label={t('incidentDetail.resolvedAt')} value={formatDate(incident.resolved_at)} />
              {(currentUser?.role === 'admin' || currentUser?.role === 'analyst') && users.length > 0 && (
                <Box sx={{ display: 'flex', gap: 2, py: 1, alignItems: 'center', borderBottom: '1px solid', borderColor: 'divider' }}>
                  <Typography sx={{ color: 'text.secondary', fontSize: '0.8rem', minWidth: 140 }}>{t('incidentDetail.assignedAnalyst')}</Typography>
                  <FormControl size="small" sx={{ minWidth: 180 }}>
                    <Select
                      value={incident.assigned_to || ''}
                      onChange={(e) => handleAssign(e.target.value || null)}
                      displayEmpty
                    >
                      <MenuItem value="">{t('incidentDetail.unassigned')}</MenuItem>
                      {users.map((u) => (
                        <MenuItem key={u.id} value={u.id}>{u.username}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
              )}
              {incident.assigned_username && currentUser?.role !== 'admin' && currentUser?.role !== 'analyst' && (
                <InfoRow label={t('incidentDetail.assignedAnalyst')} value={incident.assigned_username} />
              )}
            </CardContent>
          </Card>

          {/* Raw Payload */}
          {incident.raw_payload && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                  <Typography variant="h6">{t('incidentDetail.rawPayload')}</Typography>
                  <Tooltip title={t('incidentDetail.copy')}>
                    <IconButton size="small" onClick={() => copyToClipboard(incident.raw_payload)}>
                      <ContentCopy sx={{ fontSize: 16 }} />
                    </IconButton>
                  </Tooltip>
                </Box>
                <Box sx={{ bgcolor: 'rgba(0,0,0,0.4)', borderRadius: 2, p: 2, fontFamily: 'monospace', fontSize: '0.78rem', color: '#00d4aa', wordBreak: 'break-all', maxHeight: 200, overflow: 'auto' }}>
                  {incident.raw_payload}
                </Box>
              </CardContent>
            </Card>
          )}

          {/* User Agent */}
          {incident.user_agent && (
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 1 }}>{t('incidentDetail.userAgent')}</Typography>
                <Typography sx={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'text.secondary', wordBreak: 'break-all' }}>
                  {incident.user_agent}
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>

        {/* Right: AI + Actions */}
        <Grid item xs={12} md={6}>
          {/* AI Explanation */}
          <Box sx={{ mb: 2 }}>
            <AIExplanationCard
              explanation={incident.explanation}
              onGenerate={handleGenerateExplanation}
              generating={generating}
            />
          </Box>

          {/* Timeline/Logs */}
          {incident.logs?.length > 0 && (
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2 }}>{t('incidentDetail.automatedActions')}</Typography>
                {incident.logs.map(log => (
                  <Box key={log.id} sx={{ mb: 1.5, pl: 2, borderLeft: '2px solid rgba(0,212,170,0.3)' }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, color: 'primary.main' }}>
                      {log.action_taken.replace(/_/g, ' ')}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
                      {log.action_detail}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#8892a4' }}>
                      {formatDate(log.action_time)} · by {log.performed_by}
                    </Typography>
                  </Box>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Notes */}
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>{t('incidentDetail.notes')}</Typography>
              {incident.notes?.map(note => (
                <Box key={note.id} sx={{ mb: 1.5, p: 1.5, bgcolor: 'rgba(255,255,255,0.04)', borderRadius: 2 }}>
                  <Typography variant="body2">{note.note_content}</Typography>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    {note.created_by} · {formatDate(note.created_at)}
                  </Typography>
                </Box>
              ))}
              <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                <TextField
                  fullWidth size="small"
                  placeholder="Add a note..."
                  multiline maxRows={3}
                  value={newNote}
                  onChange={e => setNewNote(e.target.value)}
                />
                <Button
                  variant="contained"
                  onClick={handleAddNote}
                  disabled={!newNote.trim() || savingNote}
                  startIcon={savingNote ? <CircularProgress size={14} color="inherit" /> : <Add />}
                  sx={{ flexShrink: 0, alignSelf: 'flex-end' }}
                >
                  {t('incidentDetail.add')}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
