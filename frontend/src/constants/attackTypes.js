/** 8 OWASP-aligned categories + CSRF (9 total). Keep in sync with backend DETECTION_PATTERNS. */
export const ATTACK_TYPES = [
  'SQL_INJECTION',
  'XSS',
  'BRUTE_FORCE',
  'PATH_TRAVERSAL',
  'COMMAND_INJECTION',
  'SCANNER',
  'LFI_RFI',
  'FILE_UPLOAD',
  'CSRF',
];

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
