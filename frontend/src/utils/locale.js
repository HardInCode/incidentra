export function getLocaleTag(language) {
  return language === 'id' ? 'id-ID' : 'en-US';
}

const NGINX_MONTH = {
  Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5,
  Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11,
};

/** Parse nginx combined log timestamp (UTC) e.g. 18/May/2026:14:27:55 +0000 */
export function parseNginxLogTime(timeStr) {
  if (!timeStr) return null;
  const m = timeStr.match(/^(\d{2})\/(\w{3})\/(\d{4}):(\d{2}):(\d{2}):(\d{2})/);
  if (!m) return null;
  const month = NGINX_MONTH[m[2]];
  if (month === undefined) return null;
  return new Date(Date.UTC(+m[3], month, +m[1], +m[4], +m[5], +m[6]));
}

export function formatLocaleDate(iso, language, options = {}) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(getLocaleTag(language), {
    timeZone: 'Asia/Jakarta',
    ...options,
  });
}

/** Format YYYY-MM-DD chart label for dashboard axes. */
export function formatChartDay(dateStr, language) {
  if (!dateStr) return '';
  const d = new Date(`${dateStr}T12:00:00Z`);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString(getLocaleTag(language), {
    timeZone: 'Asia/Jakarta',
    month: 'short',
    day: 'numeric',
  });
}

/** Live Traffic: show log UTC timestamps in app locale (WIB), same as Incidents. */
export function formatLogTime(timeStr, language, options = {}) {
  const parsed = parseNginxLogTime(timeStr);
  if (!parsed) return timeStr || '—';
  return parsed.toLocaleString(getLocaleTag(language), {
    timeZone: 'Asia/Jakarta',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    ...options,
  });
}
