import type { Metadata } from 'next'
import { loadData, type Constituent } from '@/lib/data'
import { COHORT_NAME, PLATFORM_NAME, compact, signedPct } from '@/lib/format'

export const metadata: Metadata = { title: 'Who is tracked | Dissident Resonance Index' }

function Accounts({ c }: { c: Constituent }) {
  if (!c.accounts.length) return <span className="muted">No verified account; tracked through Wikipedia and news</span>
  return (
    <>
      {c.accounts.map((a) => (
        <div key={a.platform}>
          {PLATFORM_NAME[a.platform]}{' '}
          {a.followers !== null ? <b>{compact(a.followers)}</b> : <span className="muted">{a.unverified ? 'not collected yet' : 'no reading'}</span>}
          {a.annual_growth !== null && (
            <span className={a.annual_growth >= 0 ? 'up' : 'down'}> {signedPct(a.annual_growth)} a year</span>
          )}
        </div>
      ))}
    </>
  )
}

function Table({ rows, showBasis }: { rows: Constituent[]; showBasis: boolean }) {
  return (
    <div className="tablewrap">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            {showBasis && <th>Tier</th>}
            <th>Accounts and followers</th>
            <th className="num">Weekly views</th>
            <th className="num">Wikipedia views a day</th>
            <th className="num">News mentions, 7 days</th>
            {showBasis && <th>Documented by</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => {
            const views = c.accounts.reduce((n, a) => n + (a.views_7d ?? 0), 0)
            const anyViews = c.accounts.some((a) => a.views_7d !== null)
            return (
              <tr key={c.id}>
                <td>
                  <span className="who">{c.name}</span>
                  <br />
                  <small>{c.kind === 'movement' ? 'Movement or narrative' : COHORT_NAME[c.cohort] ?? c.cohort}</small>
                </td>
                {showBasis && <td><span className={`tag ${c.tier}`}>{c.tier}</span></td>}
                <td><Accounts c={c} /></td>
                <td className="num">{anyViews ? compact(views) : <span className="muted">n/a</span>}</td>
                <td className="num">{c.wiki_daily !== null ? compact(c.wiki_daily) : <span className="muted">n/a</span>}</td>
                <td className="num">{c.news_7d !== null ? compact(c.news_7d) : <span className="muted">n/a</span>}</td>
                {showBasis && (
                  <td>
                    {c.basis.map((b, i) => (
                      <div key={i}>
                        <a href={b.url} rel="noreferrer">{b.org}</a>
                      </div>
                    ))}
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function Page() {
  const data = loadData()
  if (!data) return <p className="empty">No dataset has been built yet.</p>
  const ext = data.constituents.filter((c) => c.basket === 'extremism')
  const order = (a: Constituent, b: Constituent) => b.weight * b.audience - a.weight * a.audience || (b.wiki_daily ?? 0) - (a.wiki_daily ?? 0)
  const people = ext.filter((c) => c.kind === 'person').sort(order)
  const movements = ext.filter((c) => c.kind === 'movement').sort(order)
  const reference = data.constituents.filter((c) => c.basket === 'reference').sort(order)
  const r = data.meta.rules
  return (
    <>
      <div className="page-head">
        <h1>Who is tracked, and on whose word</h1>
        <p>
          {people.length} people and {movements.length} movements make up the extremism basket. Each is there because a monitoring organisation
          has published a profile of it, linked in the last column. Those characterisations belong to the organisations that made them; the index
          measures audience, it does not judge anyone.
        </p>
      </div>

      <section className="section">
        <h2>Rules of inclusion</h2>
        <div className="grid2">
          <div className="panel">
            <h3>Core, counted in full</h3>
            <p className="sub" style={{ fontSize: '0.92rem' }}>{r.core}</p>
            <h3 style={{ marginTop: '1rem' }}>Adjacent, counted at half</h3>
            <p className="sub" style={{ fontSize: '0.92rem' }}>{r.adjacent}</p>
          </div>
          <div className="panel">
            <h3>Left out on purpose</h3>
            <p className="sub" style={{ fontSize: '0.92rem' }}>{r.exclusions}</p>
            <h3 style={{ marginTop: '1rem' }}>Accounts</h3>
            <p className="sub" style={{ fontSize: '0.92rem' }}>{r.accounts}</p>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>People</h2>
        <Table rows={people} showBasis />
      </section>

      <section className="section">
        <h2>Movements and narratives</h2>
        <p className="lede">These have no accounts of their own in the registry. They feed the Heat pillar through Wikipedia and news coverage.</p>
        <Table rows={movements} showBasis />
      </section>

      <section className="section">
        <h2>Mainstream reference basket</h2>
        <p className="lede">
          Large US news and commentary outlets from across the spectrum. Reach, Engagement and Mainstreaming are all expressed as a share of the
          extremism basket plus this one.
        </p>
        <Table rows={reference} showBasis={false} />
      </section>
    </>
  )
}
