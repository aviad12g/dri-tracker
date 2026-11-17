import type { CSSProperties } from 'react'
import type { Pillar } from '@/lib/data'
import { pct, rawSentence } from '@/lib/format'

/**
 * One pillar on the shared 0-100 scale. The middle cell stretches to the full row height, so the
 * grid, the robustness band and the composite's needle (drawn by the cell itself) run unbroken
 * from row to row. `mid` adds the dashed line at 50, where the pillar means parity or no change.
 */
export function PillarRow({ p, mid, i }: { p: Pillar; mid: boolean; i: number }) {
  const s = p.score
  return (
    <div className="row3 prow" style={{ '--i': i } as CSSProperties}>
      <div className="pname">
        {p.label}
        <small>{p.headline}</small>
      </div>
      <div className="scale-cell" role={s !== null ? 'img' : undefined} aria-label={s !== null ? `${p.label}: ${s.toFixed(1)} out of 100` : undefined}>
        {mid && <span className="midline" />}
        {s !== null ? (
          <>
            <span className="track" />
            <span className="dot" style={{ left: `${s}%` }} />
            <span className="val" style={s > 86 ? { right: `calc(${100 - s}% + 12px)` } : { left: `calc(${s}% + 12px)` }}>
              {s.toFixed(1)}
            </span>
          </>
        ) : (
          <>
            <span className="track off" />
            <span className="none">Not published today</span>
          </>
        )}
      </div>
      <div className="pread">
        {s !== null ? rawSentence(p.id, p.raw, p.detail) : <span className="why">{p.reason ? p.reason.charAt(0).toUpperCase() + p.reason.slice(1) + '.' : ''}</span>}
        <div className="pmeta">
          <span>Weight {pct(p.weight)}</span>
          <span>
            Inputs observed {pct(p.coverage)}
            <span className="meter" aria-hidden="true">
              <i style={{ width: `${Math.round(p.coverage * 100)}%` }} />
            </span>
          </span>
        </div>
      </div>
    </div>
  )
}
