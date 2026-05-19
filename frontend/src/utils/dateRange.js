/** Format ISO UTC for <input type="datetime-local"> (browser local timezone). */
export function isoToDatetimeLocal(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** Parse datetime-local value to ISO UTC for API. */
export function datetimeLocalToIso(localValue) {
  if (!localValue) return '';
  const d = new Date(localValue);
  if (Number.isNaN(d.getTime())) return '';
  return d.toISOString();
}

/** Inclusive end of the local calendar day for a given ISO instant. */
export function endOfLocalDayIso(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  d.setHours(23, 59, 59, 999);
  return d.toISOString();
}

/** Start of the local calendar day. */
export function startOfLocalDayIso(isoOrDate = new Date()) {
  const d = isoOrDate instanceof Date ? new Date(isoOrDate) : new Date(isoOrDate);
  if (Number.isNaN(d.getTime())) return '';
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

export function getDateRange(preset) {
  const now = new Date();
  if (preset === 'today') {
    return { date_from: startOfLocalDayIso(now), date_to: now.toISOString() };
  }
  if (preset === '7d') {
    const start = new Date(now);
    start.setDate(start.getDate() - 7);
    start.setHours(0, 0, 0, 0);
    return { date_from: start.toISOString(), date_to: now.toISOString() };
  }
  if (preset === '30d') {
    const start = new Date(now);
    start.setDate(start.getDate() - 30);
    start.setHours(0, 0, 0, 0);
    return { date_from: start.toISOString(), date_to: now.toISOString() };
  }
  return { date_from: '', date_to: '' };
}

/** Normalize custom range before API: inclusive local end-of-day when "to" is midnight. */
export function normalizeCustomRange(dateFrom, dateTo) {
  let from = dateFrom || '';
  let to = dateTo || '';
  if (to) {
    const d = new Date(to);
    if (!Number.isNaN(d.getTime()) && d.getHours() === 0 && d.getMinutes() === 0) {
      to = endOfLocalDayIso(to);
    }
  }
  if (from && to && new Date(from) > new Date(to)) {
    return { date_from: to, date_to: from, swapped: true };
  }
  return { date_from: from, date_to: to, swapped: false };
}
