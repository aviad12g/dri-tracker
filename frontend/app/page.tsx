import Link from 'next/link'
import { LineChart } from '@/components/LineChart'
import { PillarRow } from '@/components/PillarRow'
import { Ruler } from '@/components/Ruler'
import { loadData } from '@/lib/data'
import { COHORT_NAME, PLATFORM_NAME, compact, longDate, pct, signed } from '@/lib/format'

const GROUPS = [
  { id: 'scale', name: 'Scale', note: 'how large it is beside mainstream media', color: 'var(--g-scale)' },
  { id: 'dynamics', name: 'Dynamics', note: 'which way it is moving', color: 'var(--g-dynamics)' },
  { id: 'structure', name: 'Structure', note: 'where its audience lives', color: 'var(--g-structure)' },
] as const

function list(names: string[]): string {
  if (names.length <= 1) return names.join('')
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

export default function Page() {
  const data = loadData()
  if (!data) {
    return (
      <div className="page-head">
        <h1>No reading yet</h1>
        <p>
          The index is computed only from recorded observations, and none have been collected. Run <code>dri collect</code> and then{' '}
          <code>dri build</code> in the backend folder.
        </p>
      </div>
    )
  }
  const { headline: h, meta, pillars } = data
  const withheld = pillars.filter((p) => !p.available).map((p) => p.label)
  const ext = data.constituents.filter((c) => c.basket === 'extremism')
  const top = [...ext].filter((c) => c.audience > 0).sort((a, b) => b.weight * b.audience - a.weight * a.audience).slice(0, 8)
  const maxAud = Math.max(...top.map((c) => c.weight * c.audience), 1)
  const maxFollow = Math.max(...data.platforms.map((p) => Math.max(p.extremism_followers, p.reference_followers)), 1)
  const scenarios = data.sensitivity.filter((s) => s.group !== 'baseline' && s.score !== null)
  const wiki = data.heat_series.wikipedia
  const news = data.heat_series.news.map((p) => ({ ...p, value: p.value * 1e4, baseline: p.baseline * 1e4 }))
  const charts = (pillars.find((p) => p.id === 'mainstreaming')?.detail.charts ?? {}) as Record<string, any>
  const names = Object.fromEntries(data.constituents.map((c) => [c.id, c]))
  const sourceBy = Object.fromEntries(data.sources.map((s) => [s.source, s]))

  return (
    <>
      <section className="instrument" aria-labelledby="reading">
        <div className="row3">
          <div>
            <p className="reading-date" id="reading">Reading for {longDate(meta.as_of)}</p>
            {h.score !== null ? (
              <p className="reading-num">{h.score.toFixed(1)}</p>
            ) : (
              <p className="reading-num withheld">Reading withheld</p>
            )}
            <p className="reading-unit">on a scale of 0 to 100</p>
          </div>
          <div className="hero-scale">
            <Ruler score={h.score} band={h.band} />
          </div>
          <div className="hero-read">
            {h.score !== null ? (
              <>
                <p>
                  Built from {h.pillars_used.length} of {pillars.length} pillars. Confidence grade <span className="grade">{h.grade}</span>:{' '}
                  {pct(h.confidence)} of the model’s inputs were observed.
                </p>
                {h.band && (
                  <p>
                    Under {scenarios.length} alternative sets of assumptions the reading stays between {h.band.low.toFixed(1)} and{' '}
                    {h.band.high.toFixed(1)}.
                  </p>
                )}
                {h.change.d7 !== null && <p>{signed(h.change.d7)} points over seven days.</p>}
              </>
            ) : (
              <p>Pillars carrying less than half of the index weight could be computed, so no composite is published.</p>
            )}
          </div>
        </div>

        <div className="pillars">
          {GROUPS.map((g) => (
            <div key={g.id}>
              <div className="group-head">
                <i style={{ background: g.color }} aria-hidden="true" />
                {g.name} <span>{g.note}</span>
              </div>
              {pillars.filter((p) => p.group === g.id).map((p) => (
                <PillarRow key={p.id} p={p} />
              ))}
            </div>
          ))}
        </div>
      </section>

      {withheld.length > 0 && (
        <p className="muted" style={{ marginTop: '0.9rem', maxWidth: '60rem' }}>
          {list(withheld)} {withheld.length === 1 ? 'is' : 'are'} not published today. A pillar is left out rather than filled in when its inputs
          were not recorded, and the remaining weights are rescaled. See <Link href="/data/">data quality</Link> for what is missing and why.
        </p>
      )}

      <section className="section">
        <h2>Public attention over the past year</h2>
        <p className="lede">
          Wikipedia and the GDELT news archive publish their own history, so these two series run back a full year. Heat compares the latest
          week with the median of the year before it.
        </p>
        <div className="grid2">
          <div className="panel">
            <h3>Wikipedia page views</h3>
            <p className="sub">Weighted daily views of the basket’s articles, seven-day mean</p>
            {wiki.length > 1 ? (
              <>
                <LineChart points={wiki} unit="views" label="Views a day" baselineLabel="trailing-year median" />
                <div className="legend">
                  <span><i />Seven-day mean</span>
                  <span><i className="dash" />Trailing-year median</span>
                </div>
              </>
            ) : (
              <p className="empty">Not enough Wikipedia history has been collected to draw this series.</p>
            )}
          </div>
          <div className="panel">
            <h3>US news coverage</h3>
            <p className="sub">Mentions per 10,000 articles monitored by GDELT, seven-day mean</p>
            {news.length > 1 ? (
              <>
                <LineChart points={news} unit="per10k" label="Mentions per 10,000 articles" baselineLabel="trailing-year median" />
                <div className="legend">
                  <span><i />Seven-day mean</span>
                  <span><i className="dash" />Trailing-year median</span>
                </div>
              </>
            ) : (
              <p className="empty">
                No news series yet. {sourceBy.gdelt?.failed.length ? 'GDELT rate-limited the last collection run; the next run retries.' : ''}
              </p>
            )}
          </div>
        </div>
      </section>

      {data.series.length > 1 && (
        <section className="section">
          <h2>The index since {longDate(data.series[0].date)}</h2>
          <div className="panel" style={{ marginTop: '1.3rem' }}>
            <LineChart points={data.series.map((s) => ({ date: s.date, value: s.score }))} unit="score" label="Index" fixedMax={100} />
          </div>
        </section>
      )}

      <section className="section">
        <h2>Where the audience sits</h2>
        <p className="lede">
          Follower counts by platform for the extremism basket and the mainstream reference basket. Depth weights each platform by how lightly it
          is moderated.
        </p>
        <div className="grid2">
          <div className="panel">
            <h3>Followers by platform</h3>
            <div className="legend">
              <span><i className="sq" />Extremism basket</span>
              <span><i className="sq ctx" />Reference basket</span>
            </div>
            <div className="bars">
              {data.platforms.map((p) => {
                const src = sourceBy[p.platform]
                return [
                  <div className="name" key={`${p.platform}-n`}>
                    {PLATFORM_NAME[p.platform]}
                    <small>depth {p.depth.toFixed(2)}</small>
                  </div>,
                  p.observed > 0 ? (
                    <div className="barpair" key={`${p.platform}-b`}>
                      <div className="bar" title={`${compact(p.extremism_followers)} followers, extremism basket`}>
                        <i style={{ width: `${(p.extremism_followers / maxFollow) * 82}%` }} />
                        <span>{compact(p.extremism_followers)}</span>
                      </div>
                      <div className="bar ctx" title={`${compact(p.reference_followers)} followers, reference basket`}>
                        <i style={{ width: `${(p.reference_followers / maxFollow) * 82}%` }} />
                        <span>{compact(p.reference_followers)}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="missing" key={`${p.platform}-b`}>
                      Not collected. {src?.skipped ?? (src?.failed[0]?.reason ? `Last attempt: ${src.failed[0].reason}.` : '')}
                    </div>
                  ),
                ]
              })}
            </div>
            <p className="foot">
              Raw follower counts across {data.platforms.reduce((n, p) => n + p.observed, 0)} of{' '}
              {data.platforms.reduce((n, p) => n + p.registered, 0)} registered accounts.
            </p>
          </div>

          <div className="panel">
            <h3>Largest audiences in the basket</h3>
            <p className="sub">Counts only the platforms that could be read, so figures marked as undercounts are floors, not totals</p>
            <div className="tablewrap">
              <table>
                <thead>
                  <tr>
                    <th>Constituent</th>
                    <th>Tier</th>
                    <th className="num">Weighted audience</th>
                    <th className="num">Share</th>
                  </tr>
                </thead>
                <tbody>
                  {top.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <span className="who">{c.name}</span>
                        <br />
                        <small>{COHORT_NAME[c.cohort] ?? c.cohort}</small>
                        {c.accounts.some((a) => a.followers === null) && (
                          <>
                            <br />
                            <small className="down">
                              Undercount: {list(c.accounts.filter((a) => a.followers === null).map((a) => PLATFORM_NAME[a.platform]))} not read
                            </small>
                          </>
                        )}
                      </td>
                      <td><span className={`tag ${c.tier}`}>{c.tier}</span></td>
                      <td className="num">
                        <span className="mini" style={{ width: `${(c.weight * c.audience / maxAud) * 70}px` }} />
                        {compact(c.weight * c.audience)}
                      </td>
                      <td className="num">{pct(c.basket_share, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="foot"><Link href="/constituents/">See everyone who is tracked and why</Link></p>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>How much the reading depends on the assumptions</h2>
        <p className="lede">
          The index rests on stated choices: pillar weights, how much an adjacent figure counts, how audiences overlap. Each row recomputes today’s
          reading with one choice changed.
        </p>
        <div className="grid2">
          <div className="panel">
            <h3>Alternative assumptions</h3>
            <div className="tablewrap">
              <table>
                <thead>
                  <tr>
                    <th>Change</th>
                    <th className="num">Reading</th>
                    <th className="num">Difference</th>
                  </tr>
                </thead>
                <tbody>
                  {scenarios.map((s) => {
                    const d = (s.score as number) - (h.score ?? 0)
                    return (
                      <tr key={s.scenario}>
                        <td>{s.scenario}</td>
                        <td className="num">{(s.score as number).toFixed(1)}</td>
                        <td className="num">{Math.abs(d) < 0.05 ? '0.0' : signed(d)}</td>
                      </tr>
                    )
                  })}
                  {scenarios.length === 0 && (
                    <tr><td colSpan={3} className="muted">Available once a composite is published.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel">
            <h3>Podcast chart positions</h3>
            <p className="sub">Apple Podcasts, United States. Lower is higher on the chart.</p>
            <div className="tablewrap">
              <table>
                <thead>
                  <tr>
                    <th>Show</th>
                    <th>Basket</th>
                    <th className="num">Top 100</th>
                    <th className="num">News 200</th>
                  </tr>
                </thead>
                <tbody>
                  {(() => {
                    const rows = new Map<string, { entity: string; show: string; top?: number; news?: number }>()
                    for (const [chart, info] of Object.entries(charts)) {
                      for (const s of info.shows as any[]) {
                        const key = `${s.entity}:${s.show}`
                        const row: { entity: string; show: string; top?: number; news?: number } = rows.get(key) ?? { entity: s.entity, show: s.show }
                        if (chart === 'top') row.top = s.rank
                        else row.news = s.rank
                        rows.set(key, row)
                      }
                    }
                    const sorted = [...rows.values()].sort((a, b) => (a.news ?? 999) - (b.news ?? 999))
                    const mine = sorted.filter((r) => names[r.entity]?.basket === 'extremism')
                    const ref = sorted.filter((r) => names[r.entity]?.basket === 'reference').slice(0, 6)
                    return [...mine, ...ref].map((r) => (
                      <tr key={`${r.entity}${r.show}`}>
                        <td><span className="who">{r.show}</span></td>
                        <td><span className={`tag ${names[r.entity]?.tier}`}>{names[r.entity]?.basket}</span></td>
                        <td className="num">{r.top ?? <span className="muted">not charted</span>}</td>
                        <td className="num">{r.news ?? <span className="muted">not charted</span>}</td>
                      </tr>
                    ))
                  })()}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </>
  )
}
