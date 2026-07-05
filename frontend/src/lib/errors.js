export function extractError(err, fallback = 'Something went wrong') {
  const d = err?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    return d.map((e) => e.msg || e.message || 'Invalid input').join(', ');
  }
  if (typeof d === 'object' && d) return d.msg || JSON.stringify(d);
  return err?.message || fallback;
}
