/**
 * Antar — Frontend clock synchronization (Phase L1b).
 * Fetches server today from /api/health once, caches in memory,
 * and falls back to browser date if unreachable.
 */

let _cachedToday = null;

export async function serverToday() {
  if (_cachedToday) return _cachedToday;
  try {
    const res = await fetch("/api/health");
    if (res.ok) {
      const data = await res.json();
      if (data.today) {
        _cachedToday = data.today;
        return _cachedToday;
      }
    }
  } catch (e) {
    // Graceful fallback to client date
  }
  _cachedToday = new Date().toISOString().slice(0, 10);
  return _cachedToday;
}
