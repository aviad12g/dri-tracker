// Read Rumble channel pages in a real browser and print one JSON capture.
//
// Rumble refuses automated clients, so its pages cannot be collected by the
// scheduled job. This snippet is run by a person, in their own browser, on any
// rumble.com page (DevTools console). It reads the public channel listing the
// page itself embeds, one page at a time with a pause between requests, and
// prints a JSON document. Save that as data/captures/rumble/<date>.json and run
//   python -m dri import-capture data/captures/rumble/<date>.json
//
// Per channel it records the exact follower count, the channel ID, views on
// the last seven days of uploads, and total views per upload week going back
// up to a year (bounded by MAX_PAGES), plus the same per upload day for the
// last five weeks, where views are still accumulating fastest. View counts are
// as of the capture. Take captures a week apart, on the same weekday: the
// build measures how much each upload week grew between two of them.
//
// A channel page can embed more than one video list (in November 2026 the
// first page carried a short list of the newest uploads followed by the main
// list). Every list on every page is read and videos are de-duplicated by ID.
// Paging stops when a whole page is older than the cutoff, so a pinned old
// video cannot end a channel early; videos older than the cutoff are ignored.
// The week where reading stopped is incomplete, so it and anything older is
// dropped: at the cutoff, or, when the page cap is hit, at the oldest video on
// the last page read (older entries above it can only be pinned videos).
(async () => {
  const HANDLES = ['nickjfuentes', 'StewPeters', 'RealCandaceO', 'TuckerCarlson', 'TateSpeech', 'BannonsWarRoom'];
  const MAX_PAGES = 22, CUTOFF_DAYS = 365, PAUSE_MS = 1200, DAILY_DAYS = 35;
  const now = Date.now(), cutoff = now - CUTOFF_DAYS * 864e5;
  const weekStart = (t) => {
    const d = new Date(t), day = (d.getUTCDay() + 6) % 7;
    return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - day)).toISOString().slice(0, 10);
  };
  const out = { captured_at: new Date(now).toISOString(), channels: {} };
  for (const handle of HANDLES) {
    const vids = {};
    let head = null, pages = 0, stopped = null, lastOldest = null;
    for (let page = 1; !stopped; page++) {
      const r = await fetch(`/c/${handle}` + (page > 1 ? `?page=${page}` : ''), { credentials: 'same-origin' });
      if (r.status !== 200) { stopped = `HTTP ${r.status} on page ${page}`; break; }
      let pageOldest = Infinity;
      const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
      const items = [...doc.querySelectorAll('script[type="application/json"]')]
        .filter((x) => x.textContent.includes('permalink_id'))
        .flatMap((x) => { try { return JSON.parse(x.textContent).items || []; } catch (e) { return []; } })
        .filter((x) => x.object_type === 'video');
      let newest = -Infinity;
      for (const it of items) {
        const t = Date.parse(it.upload_date);
        if (!isFinite(t) || typeof it.views !== 'number') continue;
        if (!head && it.by && String(it.by.relative_url).toLowerCase() === `/c/${handle}`.toLowerCase())
          head = { id: it.by.id, name: it.by.name, followers: it.by.followers, verified: !!it.by.verified_badge };
        newest = Math.max(newest, t);
        pageOldest = Math.min(pageOldest, t);
        if (t >= cutoff) vids[it.id] = [t, it.views];
      }
      if (isFinite(pageOldest)) lastOldest = pageOldest;
      pages = page;
      if (!items.length) stopped = `no videos on page ${page}`;
      else if (newest < cutoff) stopped = 'reached cutoff';
      else if (page >= MAX_PAGES) stopped = 'page cap';
      else await new Promise((res) => setTimeout(res, PAUSE_MS));
    }
    // Where reading stopped part-way through a week: none if the channel's whole history was read.
    const cutWeek = stopped === 'reached cutoff' ? weekStart(cutoff)
      : stopped && stopped.startsWith('no videos') ? null
      : lastOldest !== null ? weekStart(lastOldest) : null;
    const keep = (week) => cutWeek === null || week > cutWeek;
    const all = Object.values(vids), weeks = {}, days = {};
    for (const [t, v] of all) {
      const w = weekStart(t); weeks[w] = weeks[w] || [0, 0]; weeks[w][0] += 1; weeks[w][1] += v;
      if (t > now - DAILY_DAYS * 864e5 && t <= now) {
        const d = new Date(t).toISOString().slice(0, 10); days[d] = days[d] || [0, 0]; days[d][0] += 1; days[d][1] += v;
      }
    }
    const recent = all.filter((x) => x[0] > now - 7 * 864e5 && x[0] <= now);
    out.channels[handle] = {
      head, pages, stopped, cut_week: cutWeek, videos: all.length,
      oldest: all.length ? new Date(Math.min(...all.map((x) => x[0]))).toISOString().slice(0, 10) : null,
      newest: all.length ? new Date(Math.max(...all.map((x) => x[0]))).toISOString().slice(0, 10) : null,
      views_7d: recent.reduce((sum, x) => sum + x[1], 0), items_7d: recent.length,
      weeks: Object.keys(weeks).sort().filter(keep).map((k) => [k, weeks[k][0], weeks[k][1]]),
      days: Object.keys(days).sort().filter((k) => keep(weekStart(Date.parse(k)))).map((k) => [k, days[k][0], days[k][1]]),
    };
  }
  console.log(JSON.stringify(out));
  return out;
})();
