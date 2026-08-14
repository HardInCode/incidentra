/**
 * Master list attack_type (9 tipe) — BUKAN tabel DB, hardcoded constant.
 * Ctrl+F: ATTACK_TYPES, DETECTION_PATTERNS, ADD_ATTACK_TYPE, RULES_FLOW
 *
 * ─── Tidak ada master rule / master attack_type table ───
 * PostgreSQL cuma punya detection_rules (rule analyst) + incidents.attack_type (string).
 * Baseline deteksi = DETECTION_PATTERNS dict di detection_engine.py (hardcoded Python).
 *
 * Tambah RULE (type sudah ada):
 *   DetectionRules.js → rules.py → detection_rules table → rules_dirty → engine reload
 *
 * Tambah TYPE baru (misal SSRF):
 *   1. Tambah 'SSRF' di array ATTACK_TYPES di bawah
 *   2. Tambah DETECTION_PATTERNS['SSRF'] di backend detection_engine.py
 *   3. (Opsional) buat rule UI attack_type=SSRF
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
