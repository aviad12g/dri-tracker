import type { Pillar } from '@/lib/data'
import { pct, rawSentence } from '@/lib/format'

const GROUP_COLOR: Record<string, string> = {
  scale: 'var(--g-scale)',
  dynamics: 'var(--g-dynamics)',
  structure: 'var(--g-structure)',
}

export function PillarRow({ p }: { p: Pillar }) {
  const s = p.score
  return (
    <div className="row3 prow">
      <div className="pname">
        {p.label}
        <small>{p.headline}</small>
      </div>
      {s !== null ? (
        <div className="strip" role="img" aria-label={`${p.label}: ${s.toFixed(1)} out of 100`}>
          <span className="dot" style={{ left: `${s}%`, background: GROUP_COLOR[p.group] }} />
          <span className="val" style={s > 86 ? { right: `calc(${100 - s}% + 12px)` } : { left: `calc(${s}% + 12px)` }}>
            {s.toFixed(1)}
          </span>
        </div>
      ) : (
        <div className="strip off">
          <span className="none">Not published</span>
        </div>
      )}
      <div className="pread">
        {s !== null ? rawSentence(p.id, p.raw, p.detail) : <span className="why">{p.reason ? p.reason.charAt(0).toUpperCase() + p.reason.slice(1) : ''}</span>}
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
