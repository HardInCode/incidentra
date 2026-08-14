/**
 * Master list attack_type (9 tipe) — BUKAN tabel DB, hardcoded constant.
 * Ctrl+F: ATTACK_TYPES, DETECTION_PATTERNS
 *
 * Harus sync dengan backend/app/core/detection_engine.py → DETECTION_PATTERNS keys.
 * Dropdown DetectionRules.js & filter Incidents pakai array ini.
 * Tambah type baru → edit file ini + DETECTION_PATTERNS di backend.
 */
export const ATTACK_TYPES = [
  'SQL_INJECTION',      // OWASP A03
  'XSS',                // OWASP A03
  'BRUTE_FORCE',        // OWASP A07 — threshold, bukan regex
  'PATH_TRAVERSAL',     // OWASP A01
  'COMMAND_INJECTION',  // OWASP A03
  'SCANNER',            // bukan OWASP Top 10 — deteksi tool recon
  'LFI_RFI',            // OWASP A03/A01
  'FILE_UPLOAD',        // OWASP insecure upload
  'CSRF',               // OWASP A01
];

/** Label untuk dialog Simulate Incident (Dashboard) */
export const SIMULATE_ATTACK_TYPES = [
  { value: 'SQL_INJECTION', label: 'SQL Injection', severity: 'Critical', desc: 'Simulates a UNION-based SQL injection attempt' },
  { value: 'XSS', label: 'Cross-Site Scripting', severity: 'High', desc: 'Simulates a script tag XSS injection' },
  { value: 'BRUTE_FORCE', label: 'Brute Force', severity: 'High', desc: 'Simulates multiple failed login attempts' },
  { value: 'PATH_TRAVERSAL', label: 'Path Traversal', severity: 'High', desc: 'Simulates directory traversal attack' },
  { value: 'COMMAND_INJECTION', label: 'Command Injection', severity: 'Critical', desc: 'Simulates OS command injection' },
  { value: 'SCANNER', label: 'Security Scanner', severity: 'Medium', desc: 'Simulates automated vulnerability scanner' },
  { value: 'LFI_RFI', label: 'LFI/RFI', severity: 'Critical', desc: 'Simulates PHP file inclusion attack' },
  { value: 'FILE_UPLOAD', label: 'File Upload', severity: 'High', desc: 'Simulates POST /files with uploaded filename in log' },
  { value: 'CSRF', label: 'Cross-Site Request Forgery', severity: 'Medium', desc: 'Simulates POST without CSRF token (vuln-web forms)' },
];
