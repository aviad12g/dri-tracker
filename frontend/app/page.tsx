import Link from 'next/link'
import { Fragment, type CSSProperties, type ReactNode } from 'react'
import { LineChart } from '@/components/LineChart'
import { PillarRow } from '@/components/PillarRow'
import { Ruler } from '@/components/Ruler'
import { Sensitivity } from '@/components/Sensitivity'
import { YearBars } from '@/components/YearBars'
import { loadData } from '@/lib/data'
import type { RumbleWeek } from '@/lib/data'
import { COHORT_NAME, PLATFORM_NAME, compact, longDate, pct, shortDate, signed, signedPct, whole } from '@/lib/format'

/** Pillar groups. `mid` names what 50 means on that group's pillars, where it means something. */
const GROUPS = [
  { id: 'scale', name: 'Scale', note: 'How large it is beside mainstream media', mid: '50 is parity with mainstream' },
  { id: 'dynamics', name: 'Dynamics', note: 'Which way it is moving', mid: '50 is steady' },
  { id: 'structure', name: 'Structure', note: 'Where its audience lives', mid: null },
] as const

const STATUS: Record<string, string> = {
  above: 'above its usual range',
  below: 'below its usual range',
  usual: 'inside its usual range',
  'no uploads': 'no uploads that week',
}

function list(names: string[]): string {
  if (names.length <= 1) return names.join('')
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}

function Readout({ score }: { score: number }) {
  const [int, dec] = score.toFixed(1).split('.')
  return (
    <p className="reading-num">
      <span className="sr">{score.toFixed(1)}</span>
      <span aria-hidden="true">
        {int}
        <span className="dec">.{dec}</span>
      </span>
    </p>
  )
}

function Chapter({ id, title, lede, children }: { id: string; title: string; lede?: ReactNode; children: ReactNode }) {
  return (
    <section className="chapter" aria-labelledby={id}>
      <div className="chapter-in">
        <header className="chapter-head">
          <h2 id={id}>{title}</h2>
          {lede && <p className="lede">{lede}</p>}
        </header>
        <div className="chapter-body">{children}</div>
      </div>
    </section>
  )
}

const isEstimate = (w: RumbleWeek) => w.maturity !== undefined && w.maturity < 1

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
  const leaders = [...ext].filter((c) => (c.basket_share ?? 0) > 0).sort((a, b) => (b.basket_share ?? 0) - (a.basket_share ?? 0)).slice(0, 2)
  const leadShare = leaders.reduce((n, c) => n + (c.basket_share ?? 0), 0)
  const maxFollow = Math.max(...data.platforms.map((p) => Math.max(p.extremism_followers, p.reference_followers)), 1)
  const scenarios = data.sensitivity.filter((s) => s.group !== 'baseline')
  const wiki = data.heat_series.wikipedia
  const news = data.heat_series.news.map((p) => ({ ...p, value: p.value * 1e4, baseline: p.baseline * 1e4 }))
  const mat = data.rumble_maturity
  const charts = (pillars.find((p) => p.id === 'mainstreaming')?.detail.charts ?? {}) as Record<string, any>
  const names = Object.fromEntries(data.constituents.map((c) => [c.id, c]))
  const sourceBy = Object.fromEntries(data.sources.map((s) => [s.source, s]))

  // The composite's needle and band, inherited by every scale cell in the pillar rows.
  const scaleVars = (h.score !== null
    ? { '--needle': `${h.score}%`, ...(h.band ? { '--band-l': `${h.band.low}%`, '--band-w': `${h.band.high - h.band.low}%` } : {}) }
    : {}) as CSSProperties
  let row = 0

  const podcastRows = (() => {
    const rows = new Map<string, { entity: string; show: string; top?: number; news?: number }>()
    for (const [chart, info] of Object.entries(charts)) {
      for (const s of info.shows as any[]) {
        const key = `${s.entity}:${s.show}`
        const r: { entity: string; show: string; top?: number; news?: number } = rows.get(key) ?? { entity: s.entity, show: s.show }
        if (chart === 'top') r.top = s.rank
        else r.news = s.rank
        rows.set(key, r)
      }
    }
    const sorted = [...rows.values()].sort((a, b) => (a.news ?? 999) - (b.news ?? 999))
    return [...sorted.filter((r) => names[r.entity]?.basket === 'extremism'), ...sorted.filter((r) => names[r.entity]?.basket === 'reference').slice(0, 5)]
  })()

  const weekOn = shortDate(addDays(meta.first_scored ?? meta.as_of, 7))
  const trend =
    h.change.d7 !== null
      ? { value: `${signed(h.change.d7)} points`, note: 'over seven days' }
      : meta.days_scored <= 1
        ? { value: 'First reading', note: `7-day change from ${weekOn}` }
        : { value: `${meta.days_scored} days of readings`, note: `7-day change from ${weekOn}` }

  return (
    <>
      <section className="instrument" aria-labelledby="thesis">
        <h1 className="thesis" id="thesis">
          A daily measure of the online audience of far-right extremism in the United States, set against mainstream media.
        </h1>

        <div className="row3 readout">
          <div>
            <p className="reading-date">Reading for {longDate(meta.as_of)}</p>
            {h.score !== null ? <Readout score={h.score} /> : <p className="reading-num withheld">Withheld</p>}
            <p className="reading-unit">on a scale of 0 to 100</p>
          </div>
          <div className="hero-scale">
            {h.score !== null && (
              <div className="legend ruler-key">
                <span><i className="needle" />Today’s reading</span>
                {h.band && <span><i className="sq wash" />Its range under other assumptions</span>}
              </div>
            )}
            <Ruler score={h.score} band={h.band} />
          </div>
          {h.score !== null ? (
            <dl className="spec">
              {h.band && (
                <>
                  <dt>Range</dt>
                  <dd>
                    {h.band.low.toFixed(1)} to {h.band.high.toFixed(1)}
                    <small>under {scenarios.filter((s) => s.score !== null).length} alternatives</small>
                  </dd>
                </>
              )}
              <dt>Confidence</dt>
              <dd>
                Grade {h.grade}
                <small>{pct(h.confidence)} of inputs observed</small>
              </dd>
              <dt>Pillars</dt>
              <dd>
                {h.pillars_used.length} of {pillars.length} published
                <small>{withheld.length ? `${list(withheld)} withheld` : 'none withheld'}</small>
              </dd>
              <dt>Trend</dt>
              <dd>
                {trend.value}
                <small>{trend.note}</small>
              </dd>
            </dl>
          ) : (
            <p className="spec">Pillars carrying less than half of the index weight could be computed, so no composite is published.</p>
          )}
        </div>

        <div className={`pillars${h.score === null ? ' no-reading' : ''}`} style={scaleVars}>
          {GROUPS.map((g) => (
            <Fragment key={g.id}>
              <div className="row3 ghead" style={{ '--i': row++ } as CSSProperties}>
                <div className="gname">
                  <b>{g.name}</b>
                  <span>{g.note}</span>
                </div>
                <div className={`scale-cell${g.mid ? '' : ' bare'}`}>
                  {g.mid && <span className="midline" />}
                  {g.mid && <span className="gref">{g.mid}</span>}
                </div>
                <div />
              </div>
              {pillars.filter((p) => p.group === g.id).map((p) => (
                <PillarRow key={p.id} p={p} mid={Boolean(g.mid)} i={row++} />
              ))}
            </Fragment>
          ))}
        </div>
      </section>

      {data.series.length > 1 && (
        <Chapter id="history" title="The reading over time" lede={`Every day since ${longDate(data.series[0].date)}, on the same 0 to 100 scale.`}>
          <LineChart points={data.series.map((s) => ({ date: s.date, value: s.score }))} unit="score" label="Index" fixedMax={100} />
        </Chapter>
      )}

      <Chapter
        id="audience"
        title="Who carries the audience"
        lede={
          leaders.length === 2
            ? `${leaders[0].name} and ${leaders[1].name} hold ${pct(leadShare)} of the basket’s weighted audience between them.`
            : 'Follower counts for the extremism basket and the mainstream reference basket.'
        }
      >
        <div className="blocks wide-left">
          <div className="block">
            <h3>Largest audiences in the basket</h3>
            <p className="sub">Only platforms that could be read are counted, so an undercount is a floor, not a total.</p>
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
                        <span className="mini" style={{ width: `${(c.weight * c.audience / maxAud) * 64}px` }} />
                        {compact(c.weight * c.audience)}
                      </td>
                      <td className="num">{pct(c.basket_share, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="foot"><Link href="/constituents/">Everyone who is tracked, and on whose word</Link></p>
          </div>

          <div className="block">
            <h3>Followers by platform</h3>
            <p className="sub">Raw counts across {data.platforms.reduce((n, p) => n + p.observed, 0)} of {data.platforms.reduce((n, p) => n + p.registered, 0)} registered accounts. Depth weights each platform by how lightly it is moderated.</p>
            <div className="legend">
              <span><i className="sq" />Extremism basket</span>
              <span><i className="sq ctx" />Mainstream reference</span>
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
                        <i style={{ width: `${(p.extremism_followers / maxFollow) * 78}%` }} />
                        <span>{compact(p.extremism_followers)}</span>
                      </div>
                      <div className="bar ctx" title={`${compact(p.reference_followers)} followers, mainstream reference`}>
                        <i style={{ width: `${(p.reference_followers / maxFollow) * 78}%` }} />
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

            <div className="block stacked">
              <h3>On the podcast charts</h3>
              <p className="sub">Apple Podcasts, United States. The Mainstreaming pillar reads these positions.</p>
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
                    {podcastRows.map((r) => (
                      <tr key={`${r.entity}${r.show}`}>
                        <td><span className="who">{r.show}</span></td>
                        <td className="muted">{names[r.entity]?.basket === 'reference' ? 'Reference' : 'Extremism'}</td>
                        <td className="num">{r.top ?? <span className="muted">none</span>}</td>
                        <td className="num">{r.news ?? <span className="muted">none</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </Chapter>

      <Chapter id="attention" title="Attention over the past year" lede="Wikipedia and the GDELT news archive keep their own history, so these run back a full year. Heat compares the latest week with the year before it.">
        <div className="blocks">
          <div className="block">
            <h3>Wikipedia page views</h3>
            <p className="sub">Weighted daily views of the basket’s articles, seven-day mean</p>
            {wiki.length > 1 ? (
              <>
                <LineChart points={wiki} unit="views" label="Views a day" baselineLabel="trailing-year median" />
                <div className="legend">
                  <span><i />Seven-day mean</span>
                  <span><i className="base" />Median of the year before</span>
                </div>
              </>
            ) : (
              <p className="empty">Not enough Wikipedia history has been collected to draw this series.</p>
            )}
          </div>
          <div className="block">
            <h3>US news coverage</h3>
            <p className="sub">Mentions per 10,000 US news articles, seven-day mean</p>
            {news.length > 1 ? (
              <>
                <LineChart points={news} unit="per10k" label="Mentions per 10,000 articles" baselineLabel="trailing-year median" />
                <div className="legend">
                  <span><i />Seven-day mean</span>
                  <span><i className="base" />Median of the year before</span>
                </div>
              </>
            ) : (
              <p className="empty">
                No news series yet. {sourceBy.gdelt?.failed.length ? 'GDELT rate-limited the last collection run; the next run retries.' : ''}
              </p>
            )}
          </div>
        </div>
      </Chapter>

      {data.rumble_upload_weeks.length > 0 && (
        <Chapter
          id="rumble"
          title="Rumble, week by week"
          lede={`Views on each week’s uploads, from a browser capture on ${longDate(data.rumble_upload_weeks[0].captured)}. Each week is set against the channel’s own average.`}
        >
          <div className="legend">
            <span><i />Views on that week’s uploads</span>
            {mat.factors.some((f) => f.m < 1) && <span><i className="est" />Still accumulating, scaled to an estimate</span>}
            <span><i className="base" />The channel’s average over the {mat.baseline_weeks} weeks before</span>
          </div>
          <div className="blocks three">
            {data.rumble_upload_weeks.map((ch) => {
              const acct = names[ch.id]?.accounts.find((a) => a.platform === 'rumble')
              const w = ch.latest
              const est = w ? isEstimate(w) : false
              const gain = data.rumble_view_gains.filter((g) => g.id === ch.id).slice(-1)[0]
              return (
                <div className="block" key={ch.id}>
                  <h3>{ch.name}</h3>
                  <p className="sub">{compact(acct?.followers ?? null)} followers, {ch.weeks.length} weeks captured</p>
                  {w && w.vs_baseline !== undefined && w.baseline !== undefined && w.adjusted !== undefined ? (
                    <div className="change">
                      <b>{signedPct(w.vs_baseline)}</b>
                      <span>
                        against its {mat.baseline_weeks}-week average, <span className="call">{STATUS[w.status ?? 'usual']}</span>
                      </span>
                    </div>
                  ) : (
                    <div className="change">
                      <b className="na">No average yet</b>
                    </div>
                  )}
                  {ch.weeks.length > 1 ? (
                    <LineChart
                      points={ch.weeks.map((x) => ({ date: x.date, value: x.adjusted ?? x.views, baseline: x.baseline, estimate: isEstimate(x) }))}
                      unit="views" label="Views on that week’s uploads" baselineLabel={`average of the ${mat.baseline_weeks} weeks before`} small />
                  ) : (
                    <p className="empty">One completed week so far.</p>
                  )}
                  <p className="foot">
                    {w && w.baseline !== undefined && w.adjusted !== undefined
                      ? `Week of ${shortDate(w.date)}: ${w.videos} ${w.videos === 1 ? 'upload' : 'uploads'}, ${est ? 'about ' : ''}${compact(w.adjusted)} views${est ? ' once settled' : ''}, against an average of ${compact(w.baseline)}.` +
                        (w.vs_baseline_low !== undefined && w.vs_baseline_low !== w.vs_baseline_high ? ` Range ${signedPct(w.vs_baseline_low)} to ${signedPct(w.vs_baseline_high)}.` : '')
                      : ch.weeks.length <= mat.baseline_min_weeks
                        ? `The capture reached back ${ch.weeks.length} weeks; an average needs ${mat.baseline_min_weeks} earlier weeks.`
                        : 'The weeks before the latest one had no uploads to average.'}
                    {gain ? ` Gained ${compact(gain.gained)} views in the ${gain.days} days to ${shortDate(gain.to)}.` : ''}
                  </p>
                </div>
              )
            })}
          </div>
          <p className="note">
            {mat.method === 'longitudinal'
              ? `Young weeks are scaled by growth measured between ${mat.captures} captures of the same uploads.`
              : `Young weeks are scaled by a provisional factor read from one capture (${mat.factors.map((f) => `${f.age === 0 ? 'the newest week' : `${f.age} ${f.age === 1 ? 'week' : 'weeks'} old`} ${pct(f.m)} complete`).join(', ')}), which a second capture replaces with measured growth.`}{' '}
            A week is called above or below only when its whole range falls outside what eight in ten of the channel’s recent weeks drew.{' '}
            <Link href="/method/#accumulation">How this is computed</Link>. These figures are not part of the index.
          </p>
        </Chapter>
      )}

      {data.offline && (
        <Chapter
          id="offline"
          title="Incidents recorded offline"
          lede={`What the ADL recorded in the United States each year since ${data.offline.first_year}. Shown beside the index, never inside it, so the two can be compared.`}
        >
          <div className="blocks">
            {data.offline.series.filter((x) => x.id !== 'extremist_violence').map((x) => {
              const all = x.id === 'extremist_violence_right_wing' ? data.offline!.series.find((y) => y.id === 'extremist_violence') : null
              const ended = x.last.slice(0, 4) < data.offline!.last.slice(0, 4)
              return (
                <div className="block" key={x.id}>
                  <h3>{x.label}</h3>
                  <p className="sub">{x.note}</p>
                  <YearBars years={x.years} label={x.label} />
                  <p className="foot">
                    {x.partial ? `${whole(x.partial.count)} recorded so far for ${x.partial.year}, which is incomplete and not drawn. ` : ''}
                    {ended ? `The ADL’s published records of this type stop in ${x.last.slice(0, 4)}. ` : ''}
                    {all ? `Across all ideologies the ADL recorded ${whole(all.total)} such incidents in these years; ${whole(x.total)} were right-wing. ` : ''}
                    {x.id === 'antisemitic_incident' ? 'Counted whoever was responsible, so this is not a measure of the far right alone.' : ''}
                  </p>
                </div>
              )
            })}
          </div>
          <p className="note">
            Source: <a href={data.offline.url}>{data.offline.source}</a>, the ADL’s published incident records, tallied by type. These are counts
            of what was reported and logged, by the ADL’s definitions, and each year is published months after it ends. A record can carry more
            than one type, so the panels should not be added together. <Link href="/method/#offline">Why these counts are kept out of the index</Link>.
          </p>
        </Chapter>
      )}

      {h.score !== null && (
        <Chapter
          id="assumptions"
          title="How much the reading depends on its assumptions"
          lede="Each row recomputes today’s reading with one stated choice changed. The crimson line is the published reading."
        >
          <Sensitivity rows={scenarios} published={h.score} />
        </Chapter>
      )}
    </>
  )
}
