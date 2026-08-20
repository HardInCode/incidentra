/**
 * SOC REST client — axios wrapper + JWT dari localStorage.
 * Ctrl+F: LOGIN_FLOW, RULES_FLOW, INCIDENTS_FLOW, INCIDENT_CONTEXT_FLOW, UNBLOCK_FLOW,
 *         NOTIFY_INAPP, SETTINGS_FLOW, CHATBOT_FLOW, IP_HISTORY_FLOW,
 *         RATE_LIMIT_FLOW, TRAFFIC_FLOW, interceptors
 */
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Request interceptor: tempel Bearer token ke setiap request ───
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('incidentra_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ─── Response interceptor: 401 → logout (kecuali saat login — biar Alert error tetap tampil) ───
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const url = err.config?.url || '';
    const isLoginAttempt = url.includes('/auth/login');

    if (status === 401 && !isLoginAttempt) {
      localStorage.removeItem('incidentra_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ─── Dashboard (Dashboard.js) ───
export const getDashboardStats = () => api.get('/dashboard/stats');
export const getRecentIncidents = () => api.get('/dashboard/recent-incidents');
export const getLogStatus = () => api.get('/dashboard/log-status');
export const getNotificationsSummary = (sinceId = 0) =>
  api.get('/notifications/summary', { params: { since_id: sinceId } });  // NOTIFY_INAPP — NotificationBell.js

// ─── Incidents (Incidents.js) — INCIDENTS_FLOW ───
// GET list dari PostgreSQL; status update → incidents.py
export const getIncidents = (params) => api.get('/incidents/', { params });
// INCIDENT_CONTEXT_FLOW — SELECT incidents (+ logs/notes/explanation) untuk Detail + chatbot context
export const getIncident = (id) => api.get(`/incidents/${id}`);
export const updateIncidentStatus = (id, status) => api.put(`/incidents/${id}/status`, { status });
export const bulkUpdateIncidentStatus = (ids, status) =>
  api.patch('/incidents/bulk-status', { ids, status });
export const assignIncident = (id, assignedTo) =>
  api.put(`/incidents/${id}/assign`, { assigned_to: assignedTo });
export const addIncidentNote = (id, content, created_by = 'admin') =>
  api.post(`/incidents/${id}/notes`, { content, created_by });
export const triggerExplanation = (id, language = 'en', force = false) =>
  api.post(`/incidents/${id}/explain`, { language, force });
export const exportIncidentsCsv = (params) =>
  api.get('/incidents/export', { params, responseType: 'blob' });

// ─── Blocked IPs (BlockedIPs.js) — UNBLOCK_FLOW ───
// unblockIP → blocked_ips.py DELETE → Redis unblocked:{ip} + dedup waiver
export const getBlockedIPs = (params) => api.get('/blocked-ips/', { params });
export const addBlockedIP = (data) => api.post('/blocked-ips/', data);
export const unblockIP = (id) => api.delete(`/blocked-ips/${id}`);
export const updateBlockedIP = (id, data) => api.patch(`/blocked-ips/${id}`, data);

// ─── Rate Limited (BlockedIPs.js tab 1) — RATE_LIMIT_FLOW ───
// JSON + Redis — bukan PostgreSQL; vuln-web return 429
export const getRateLimitedIPs = (params) => api.get('/rate-limited/', { params });
export const clearRateLimit = (ip) => api.delete(`/rate-limited/${encodeURIComponent(ip)}`);
export const extendRateLimit = (ip, data) => api.patch(`/rate-limited/${encodeURIComponent(ip)}`, data);

// ─── Detection Rules (DetectionRules.js) — RULES_FLOW ───
// createRule/updateRule/deleteRule → backend/app/api/rules.py → PostgreSQL detection_rules + rules_dirty
export const getRules = (params) => api.get('/rules/', { params });
export const createRule = (data) => api.post('/rules/', data);
export const updateRule = (id, data) => api.put(`/rules/${id}`, data);
export const deleteRule = (id) => api.delete(`/rules/${id}`);

// ─── IP History (IPHistoryDrawer.js) — IP_HISTORY_FLOW ───
export const getIPHistory = (ip, lang = 'en') =>
  api.get(`/ip/${ip}/history`, { params: { lang } });

// ─── Live Traffic (LiveTraffic.js) — TRAFFIC_FLOW ───
export const getRecentTraffic = (limit = 100) => api.get('/traffic/recent', { params: { limit } });

// Sandbox regex — RULES_FLOW (tanpa INSERT incident)
export const testPayload = (data) => api.post('/detection/test', data);
// SIMULATE_FLOW — INSERT incident + respond() langsung (Incidents.js)
export const simulateAttack = (data) => api.post('/detection/simulate', data);
// INJECT_FLOW — tulis access.log + PIPELINE penuh
export const injectLog = (data) => api.post('/detection/inject-log', data);

// ─── Chatbot (ChatbotWidget.js) — CHATBOT_FLOW + INCIDENT_CONTEXT_FLOW ───
// Body: { message, session_id, context? }
// context = JSON.stringify(incident) dari ChatbotContext — chatbot.py sisipkan ke full_message Groq
export const sendChatMessage = (data) => api.post('/chatbot/message', data);

// ─── Auth (Login.js) — LOGIN_FLOW ───
// login → auth.py POST /login → JWT; interceptor bawah tempel Bearer ke semua request
export const login = (username, password) => api.post('/auth/login', { username, password });
export const register = (data) => api.post('/auth/register', data);
export const forgotPassword = (email) => api.post('/auth/forgot-password', { email });
export const resetPassword = (data) => api.post('/auth/reset-password', data);
export const getSupportContact = () => api.get('/auth/support-contact');
export const getUsers = () => api.get('/auth/users');

// User Management (admin only)
export const listUsers = (params) => api.get('/users/', { params });
export const createUser = (data) => api.post('/users/', data);
export const updateUser = (id, data) => api.patch(`/users/${id}`, data);
export const resetUserPassword = (id, data) => api.post(`/users/${id}/reset-password`, data);
export const deleteUser = (id) => api.delete(`/users/${id}`);

// Audit
export const getAuditLogs = (params) => api.get('/audit/', { params });

// ─── Settings (Settings.js) — SETTINGS_FLOW ───
export const getSettings = () => api.get('/settings/');
export const updateSettings = (data) => api.put('/settings/', data);
export const testNotification = (channel) => api.post('/settings/test/notification', { channel });  // NOTIFY test
export const testAbuseIPDB = () => api.post('/settings/test/abuseipdb');
export const testGroq = (data) => api.post('/settings/test/groq', data);  // CHATBOT + AI explain provider

export default api;
