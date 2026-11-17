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
// up to a year (bounded by MAX_PAGES). View counts are as of the capture.
(async () => {
  const HANDLES = ['nickjfuentes', 'StewPeters', 'RealCandaceO', 'TuckerCarlson', 'TateSpeech', 'BannonsWarRoom'];
  const MAX_PAGES = 22, CUTOFF_DAYS = 365, PAUSE_MS = 1200;
  const now = Date.now(), cutoff = now - CUTOFF_DAYS * 864e5;
  const weekStart = (t) => {
    const d = new Date(t), day = (d.getUTCDay() + 6) % 7;
    return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - day)).toISOString().slice(0, 10);
  };
  const out = { captured_at: new Date(now).toISOString(), channels: {} };
  for (const handle of HANDLES) {
    const vids = {};
    let head = null, pages = 0, stopped = null;
    for (let page = 1; !stopped; page++) {
      const r = await fetch(`/c/${handle}` + (page > 1 ? `?page=${page}` : ''), { credentials: 'same-origin' });
      if (r.status !== 200) { stopped = `HTTP ${r.status} on page ${page}`; break; }
      const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
      const s = [...doc.querySelectorAll('script[type="application/json"]')].find((x) => x.textContent.includes('permalink_id'));
      const items = s ? (JSON.parse(s.textContent).items || []).filter((x) => x.object_type === 'video') : [];
      let oldest = Infinity;
      for (const it of items) {
        const t = Date.parse(it.upload_date);
        if (!isFinite(t) || typeof it.views !== 'number') continue;
        if (!head && it.by && String(it.by.relative_url).toLowerCase() === `/c/${handle}`.toLowerCase())
          head = { id: it.by.id, name: it.by.name, followers: it.by.followers, verified: !!it.by.verified_badge };
        vids[it.id] = [t, it.views];
        oldest = Math.min(oldest, t);
      }
      pages = page;
      if (!items.length) stopped = `no videos on page ${page}`;
      else if (oldest < cutoff) stopped = 'reached cutoff';
      else if (page >= MAX_PAGES) stopped = 'page cap';
      else await new Promise((res) => setTimeout(res, PAUSE_MS));
    }
    const all = Object.values(vids), weeks = {};
    for (const [t, v] of all) { const w = weekStart(t); weeks[w] = weeks[w] || [0, 0]; weeks[w][0] += 1; weeks[w][1] += v; }
    const recent = all.filter((x) => x[0] > now - 7 * 864e5 && x[0] <= now);
    out.channels[handle] = {
      head, pages, stopped, videos: all.length,
      oldest: all.length ? new Date(Math.min(...all.map((x) => x[0]))).toISOString().slice(0, 10) : null,
      newest: all.length ? new Date(Math.max(...all.map((x) => x[0]))).toISOString().slice(0, 10) : null,
      views_7d: recent.reduce((sum, x) => sum + x[1], 0), items_7d: recent.length,
      // The oldest week is dropped: the listing was cut off part-way through it.
      weeks: Object.keys(weeks).sort().slice(1).map((k) => [k, weeks[k][0], weeks[k][1]]),
    };
  }
  console.log(JSON.stringify(out));
  return out;
})();
