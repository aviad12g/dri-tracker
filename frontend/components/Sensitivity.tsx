import { Fragment, type CSSProperties } from 'react'
import { signed } from '@/lib/format'

type Scenario = { group: string; scenario: string; score: number | null }

const GROUPS: { id: string; label: string }[] = [
  { id: 'weights', label: 'Pillar weights' },
  { id: 'basket', label: 'How much an adjacent figure counts' },
  { id: 'overlap', label: 'How far one person’s audiences overlap' },
  { id: 'views', label: 'What a Telegram view is worth' },
]

/**
 * Every alternative assumption as a dot on a zoomed scale, with the published reading as the crimson
 * needle running down the column. Uses the same scale-cell drawing as the pillar rows.
 */
export function Sensitivity({ rows, published }: { rows: Scenario[]; published: number }) {
  const scored = rows.filter((r): r is Scenario & { score: number } => r.score !== null)
  if (!scored.length) return <p className="empty">Available once a composite is published.</p>
  const vals = [published, ...scored.map((r) => r.score)]
  const lo = Math.floor((Math.min(...vals) - 1) / 5) * 5
  const hi = Math.ceil((Math.max(...vals) + 1) / 5) * 5
  const pos = (v: number) => ((v - lo) / (hi - lo)) * 100
  const ticks: number[] = []
  for (let t = lo; t <= hi; t += 5) ticks.push(t)
  const vars = { '--needle': `${pos(published)}%`, '--step': `${100 / (ticks.length - 1)}%` } as CSSProperties
  const groups = GROUPS.filter((g) => scored.some((r) => r.group === g.id))

  return (
    <div className="dots" style={vars}>
      <div className="dots-row dots-axis" aria-hidden="true">
        <div />
        <div className="scale-cell">
          {ticks.filter((t) => Math.abs(pos(t) - pos(published)) > 6).map((t) => (
            <span key={t} style={{ left: `${pos(t)}%` }}>{t}</span>
          ))}
          <span className="pub" style={{ left: `${pos(published)}%` }}>{published.toFixed(1)}</span>
        </div>
        <div />
      </div>
      {groups.map((g) => (
        <Fragment key={g.id}>
          <div className="dots-row group">
            <div>{g.label}</div>
            <div className="scale-cell" />
            <div />
          </div>
          {scored.filter((r) => r.group === g.id).map((r) => {
            const d = r.score - published
            return (
              <div className="dots-row" key={r.scenario}>
                <div className="dots-label">{r.scenario}</div>
                <div className="scale-cell" role="img" aria-label={`${r.scenario}: ${r.score.toFixed(1)}`}>
                  <i style={{ left: `${pos(r.score)}%` }} />
                </div>
                <div className="dots-val">
                  {r.score.toFixed(1)}
                  <small>{Math.abs(d) < 0.05 ? '0.0' : signed(d)}</small>
                </div>
              </div>
            )
          })}
        </Fragment>
      ))}
    </div>
  )
}
