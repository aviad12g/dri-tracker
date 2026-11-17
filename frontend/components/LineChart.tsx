'use client'

import { useMemo, useRef, useState } from 'react'

type Point = { date: string; value: number; baseline?: number }

const M = { top: 14, right: 62, bottom: 30, left: 50 }
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function niceMax(v: number): number {
  const mag = Math.pow(10, Math.floor(Math.log10(v)))
  for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * mag >= v) return m * mag
  return 10 * mag
}

function fmt(v: number, unit: string): string {
  if (unit === 'views') return v >= 1e6 ? `${(v / 1e6).toFixed(v >= 1e7 ? 1 : 2).replace(/\.?0+$/, '')}M` : v >= 1e3 ? `${(v / 1e3).toFixed(v >= 1e4 ? 0 : 1)}K` : `${Math.round(v)}`
  if (unit === 'per10k') return v.toFixed(v >= 10 ? 1 : 2)
  return v.toFixed(1)
}

/** A single series over time with an optional reference line, a crosshair and a tooltip. */
export function LineChart({ points, unit, label, baselineLabel, fixedMax, maxTicks = 7, small = false }: {
  points: Point[]
  unit: 'views' | 'per10k' | 'score'
  label: string
  baselineLabel?: string
  fixedMax?: number
  maxTicks?: number
  small?: boolean
}) {
  // A chart shown in a narrow column uses a smaller drawing area so its text stays legible.
  const W = small ? 400 : 640
  const H = small ? 230 : 260
  const [hover, setHover] = useState<number | null>(null)
  const ref = useRef<SVGSVGElement>(null)
  const geo = useMemo(() => {
    const n = points.length
    const max = fixedMax ?? niceMax(Math.max(...points.map((p) => Math.max(p.value, p.baseline ?? 0))) * 1.05)
    const x = (i: number) => M.left + (n === 1 ? 0.5 : i / (n - 1)) * (W - M.left - M.right)
    const y = (v: number) => H - M.bottom - (v / max) * (H - M.top - M.bottom)
    const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join('')
    // The reference line is drawn only where a reference exists; a gap starts a new stroke.
    let base: string | null = null
    if (points.some((p) => p.baseline !== undefined)) {
      base = ''
      points.forEach((p, i) => {
        if (p.baseline === undefined) return
        base += `${i > 0 && points[i - 1].baseline !== undefined ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.baseline).toFixed(1)}`
      })
    }
    const months: { i: number; text: string }[] = []
    points.forEach((p, i) => {
      // Label the first point of each month (daily series hit the 1st; weekly series do not).
      if (i > 0 && p.date.slice(0, 7) !== points[i - 1].date.slice(0, 7)) {
        const m = Number(p.date.slice(5, 7))
        months.push({ i, text: MONTHS[m - 1] + (m === 1 ? ` ${p.date.slice(0, 4)}` : '') })
      }
    })
    const step = Math.max(1, Math.ceil(months.length / maxTicks))
    return { n, max, x, y, line, base, months: months.filter((_, k) => k % step === 0) }
  }, [points, fixedMax, maxTicks, W, H])

  if (!points.length) return null
  const last = points[points.length - 1]
  const h = hover === null ? null : points[hover]

  function move(e: React.PointerEvent<SVGSVGElement>) {
    const box = ref.current!.getBoundingClientRect()
    const px = ((e.clientX - box.left) / box.width) * W
    const t = (px - M.left) / (W - M.left - M.right)
    setHover(Math.max(0, Math.min(geo.n - 1, Math.round(t * (geo.n - 1)))))
  }

  return (
    <div className="chart">
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${label}, ${points[0].date} to ${last.date}. Latest value ${fmt(last.value, unit)}.`}
        onPointerMove={move} onPointerLeave={() => setHover(null)}>
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <g key={f}>
            <line x1={M.left} x2={W - M.right} y1={geo.y(geo.max * f)} y2={geo.y(geo.max * f)} stroke={f === 0 ? 'var(--ink-3)' : 'var(--rule-soft)'} strokeWidth={1} />
            <text x={M.left - 8} y={geo.y(geo.max * f) + 4} textAnchor="end">{fmt(geo.max * f, unit)}</text>
          </g>
        ))}
        {geo.months.map((m) => (
          <text key={m.i} x={geo.x(m.i)} y={H - 8} textAnchor="middle">{m.text}</text>
        ))}
        {geo.base && <path d={geo.base} fill="none" stroke="var(--context)" strokeWidth={2} strokeDasharray="5 4" />}
        <path d={geo.line} fill="none" stroke="var(--series-1)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={geo.x(geo.n - 1)} cy={geo.y(last.value)} r={4.5} fill="var(--series-1)" stroke="var(--surface)" strokeWidth={2} />
        <text className="now" x={geo.x(geo.n - 1) + 9} y={geo.y(last.value) + 4}>{fmt(last.value, unit)}</text>
        {h && hover !== null && (
          <g>
            <line x1={geo.x(hover)} x2={geo.x(hover)} y1={M.top} y2={H - M.bottom} stroke="var(--ink-2)" strokeWidth={1} />
            <circle cx={geo.x(hover)} cy={geo.y(h.value)} r={4.5} fill="var(--series-1)" stroke="var(--surface)" strokeWidth={2} />
          </g>
        )}
      </svg>
      {h && hover !== null && (
        <div className="tip" style={{ left: `${(geo.x(hover) / W) * 100}%`, top: `${(geo.y(h.value) / H) * 100}%`, marginTop: -10 }}>
          {h.date}
          <br />
          <b>{fmt(h.value, unit)}</b> {label.toLowerCase()}
          {h.baseline !== undefined && (
            <>
              <br />
              {fmt(h.baseline, unit)} {baselineLabel}
            </>
          )}
        </div>
      )}
    </div>
  )
}
