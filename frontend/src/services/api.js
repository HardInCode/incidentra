/**
 * SOC REST client — JWT from localStorage.
 * SIDANG: rules CRUD, settings, traffic, incidents, blocked IPs.
 */
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('incidentra_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const url = err.config?.url || '';
    const isLoginAttempt = url.includes('/auth/login');

    // Wrong password on login returns 401 — do not hard-redirect (that reloads the page and clears the error Alert).
    if (status === 401 && !isLoginAttempt) {
      localStorage.removeItem('incidentra_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// Dashboard
export const getDashboardStats = () => api.get('/dashboard/stats');
export const getRecentIncidents = () => api.get('/dashboard/recent-incidents');
export const getLogStatus = () => api.get('/dashboard/log-status');
export const getNotificationsSummary = (sinceId = 0) =>
  api.get('/notifications/summary', { params: { since_id: sinceId } });

// Incidents
export const getIncidents = (params) => api.get('/incidents/', { params });
export const getIncident = (id) => api.get(`/incidents/${id}`);
export const updateIncidentStatus = (id, status) => api.put(`/incidents/${id}/status`, { status });
export const bulkUpdateIncidentStatus = (ids, status) =>
  api.patch('/incidents/bulk-status', { ids, status });
export const assignIncident = (id, assignedTo) =>
  api.put(`/incidents/${id}/assign`, { assigned_to: assignedTo });
export const addIncidentNote = (id, content, created_by = 'admin') =>
  api.post(`/incidents/${id}/notes`, { content, created_by });
export const triggerExplanation = (id, language = 'en') =>
  api.post(`/incidents/${id}/explain`, { language });
export const exportIncidentsCsv = (params) =>
  api.get('/incidents/export', { params, responseType: 'blob' });

// Blocked IPs
// REVISI 1C: support query params (sort_by, sort_dir, block_type, search)
export const getBlockedIPs = (params) => api.get('/blocked-ips/', { params });
export const addBlockedIP = (data) => api.post('/blocked-ips/', data);
export const unblockIP = (id) => api.delete(`/blocked-ips/${id}`);
export const updateBlockedIP = (id, data) => api.patch(`/blocked-ips/${id}`, data);

// Rate limited IPs (JSON + Redis; no DB)
export const getRateLimitedIPs = (params) => api.get('/rate-limited/', { params });
export const clearRateLimit = (ip) => api.delete(`/rate-limited/${encodeURIComponent(ip)}`);
export const extendRateLimit = (ip, data) => api.patch(`/rate-limited/${encodeURIComponent(ip)}`, data);

// Detection Rules
// REVISI 1B: support query params (sort_by, sort_dir, is_active, attack_type)
export const getRules = (params) => api.get('/rules/', { params });
export const createRule = (data) => api.post('/rules/', data);
export const updateRule = (id, data) => api.put(`/rules/${id}`, data);
export const deleteRule = (id) => api.delete(`/rules/${id}`);

// IP History — REVISI 2
export const getIPHistory = (ip, lang = 'en') =>
  api.get(`/ip/${ip}/history`, { params: { lang } });

// Live Traffic
export const getRecentTraffic = (limit = 100) => api.get('/traffic/recent', { params: { limit } });

// Detection testing
export const testPayload = (data) => api.post('/detection/test', data);
export const simulateAttack = (data) => api.post('/detection/simulate', data);
export const injectLog = (data) => api.post('/detection/inject-log', data);

// Chatbot
export const sendChatMessage = (data) => api.post('/chatbot/message', data);

// Auth
export const login = (username, password) => api.post('/auth/login', { username, password });
export const getUsers = () => api.get('/auth/users');

// Audit
export const getAuditLogs = (params) => api.get('/audit/', { params });

// Settings
export const getSettings = () => api.get('/settings/');
export const updateSettings = (data) => api.put('/settings/', data);
export const testNotification = (channel) => api.post('/settings/test/notification', { channel });
export const testAbuseIPDB = () => api.post('/settings/test/abuseipdb');
export const testGroq = (data) => api.post('/settings/test/groq', data);

export default api;
