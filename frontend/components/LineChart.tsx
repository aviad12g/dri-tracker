'use client'

import { useEffect, useMemo, useRef, useState } from 'react'

/** `estimate` marks a point that is a modelled value rather than a recorded one; it is drawn dotted. */
type Point = { date: string; value: number; baseline?: number; estimate?: boolean }

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** A rounded axis: the smallest step of 1, 2, 2.5 or 5 times a power of ten that covers the data in at most `most` intervals. */
function niceScale(raw: number, most: number): { max: number; ticks: number[] } {
  if (!(raw > 0)) return { max: 1, ticks: [0, 1] }
  const mag = Math.pow(10, Math.floor(Math.log10(raw / most)))
  for (const k of [1, 2, 2.5, 5, 10, 20, 25, 50]) {
    const step = k * mag
    const n = Math.max(1, Math.ceil(raw / step - 1e-9))
    if (n <= most) return { max: n * step, ticks: Array.from({ length: n + 1 }, (_, i) => i * step) }
  }
  return { max: raw, ticks: [0, raw] }
}

function fmt(v: number, unit: string): string {
  if (unit === 'views') return v >= 1e6 ? `${(v / 1e6).toFixed(v >= 1e7 ? 1 : 2).replace(/\.?0+$/, '')}M` : v >= 1e3 ? `${(v / 1e3).toFixed(v >= 1e4 ? 0 : 1)}K` : `${Math.round(v)}`
  if (unit === 'per10k') return v.toFixed(v >= 10 ? 1 : 2)
  return v.toFixed(1)
}

function path(pts: [number, number][]): string {
  return pts.map(([px, py], i) => `${i ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`).join('')
}

/**
 * A single series over time with an optional reference line, a crosshair and a tooltip. The SVG is
 * drawn at the width it is shown at, so its text stays at its stated size on a phone and on a wide screen.
 */
export function LineChart({ points, unit, label, baselineLabel, fixedMax, small = false }: {
  points: Point[]
  unit: 'views' | 'per10k' | 'score'
  label: string
  baselineLabel?: string
  fixedMax?: number
  small?: boolean
}) {
  const box = useRef<HTMLDivElement>(null)
  const svg = useRef<SVGSVGElement>(null)
  const [width, setWidth] = useState<number | null>(null)
  const [hover, setHover] = useState<number | null>(null)

  useEffect(() => {
    const el = box.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver((entries) => {
      const w = Math.round(entries[0].contentRect.width)
      if (w > 0) setWidth(w)
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const W = width ?? (small ? 340 : 560)
  const H = small ? 176 : 228
  const M = { top: 12, right: small ? 50 : 58, bottom: 26, left: small ? 38 : 44 }

  const geo = useMemo(() => {
    const n = points.length
    const scale = fixedMax
      ? { max: fixedMax, ticks: [0, 0.25, 0.5, 0.75, 1].map((f) => f * fixedMax) }
      : niceScale(Math.max(...points.map((p) => Math.max(p.value, p.baseline ?? 0))) * 1.04, small ? 3 : 5)
    const max = scale.max
    const x = (i: number) => M.left + (n === 1 ? 0.5 : i / (n - 1)) * (W - M.left - M.right)
    const y = (v: number) => H - M.bottom - (v / max) * (H - M.top - M.bottom)
    const firstEst = points.findIndex((p) => p.estimate)
    const cut = firstEst === -1 ? n : Math.max(firstEst, 1)
    const xy = points.map((p, i) => [x(i), y(p.value)] as [number, number])
    const recorded = path(xy.slice(0, cut))
    const estimated = cut < n ? path(xy.slice(cut - 1)) : null
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
    // Keep month labels at least ~64px apart at the width the chart is drawn.
    const room = Math.max(1, Math.floor((W - M.left - M.right) / 64))
    const step = Math.max(1, Math.ceil(months.length / room))
    return { n, max, x, y, recorded, estimated, base, yTicks: scale.ticks, months: months.filter((_, k) => k % step === 0) }
  }, [points, fixedMax, small, W, H, M.left, M.right, M.top, M.bottom])

  if (!points.length) return null
  const last = points[points.length - 1]
  const h = hover === null ? null : points[hover]

  function move(e: React.PointerEvent<SVGSVGElement>) {
    const r = svg.current!.getBoundingClientRect()
    const px = ((e.clientX - r.left) / r.width) * W
    const t = (px - M.left) / (W - M.left - M.right)
    setHover(Math.max(0, Math.min(geo.n - 1, Math.round(t * (geo.n - 1)))))
  }

  return (
    <div className="chart" ref={box}>
      <svg ref={svg} width="100%" height={H} viewBox={`0 0 ${W} ${H}`} role="img"
        aria-label={`${label}, ${points[0].date} to ${last.date}. Latest value ${last.estimate ? 'about ' : ''}${fmt(last.value, unit)}.`}
        onPointerMove={move} onPointerLeave={() => setHover(null)}>
        {geo.yTicks.map((t) => (
          <g key={t}>
            <line x1={M.left} x2={W - M.right} y1={geo.y(t)} y2={geo.y(t)} stroke={t === 0 ? 'var(--ink-3)' : 'var(--rule-soft)'} strokeWidth={t === 0 ? 1.5 : 1} />
            <text x={M.left - 8} y={geo.y(t) + 4} textAnchor="end">{Number.isInteger(t) && unit !== 'views' ? t : fmt(t, unit)}</text>
          </g>
        ))}
        {geo.months.map((m) => (
          <text key={m.i} x={geo.x(m.i)} y={H - 7} textAnchor="middle">{m.text}</text>
        ))}
        {geo.base && <path d={geo.base} fill="none" stroke="var(--context)" strokeWidth={2} strokeDasharray="6 4" />}
        <path d={geo.recorded} fill="none" stroke="var(--online)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {geo.estimated && <path d={geo.estimated} fill="none" stroke="var(--online)" strokeWidth={2.5} strokeDasharray="0.5 5" strokeLinecap="round" />}
        <circle cx={geo.x(geo.n - 1)} cy={geo.y(last.value)} r={4.5} fill={last.estimate ? 'var(--bg)' : 'var(--online)'} stroke={last.estimate ? 'var(--online)' : 'var(--bg)'} strokeWidth={2} />
        <text className="now" x={geo.x(geo.n - 1) + 9} y={geo.y(last.value) + 4}>{last.estimate ? '≈' : ''}{fmt(last.value, unit)}</text>
        {h && hover !== null && (
          <g>
            <line x1={geo.x(hover)} x2={geo.x(hover)} y1={M.top} y2={H - M.bottom} stroke="var(--ink-2)" strokeWidth={1} />
            <circle cx={geo.x(hover)} cy={geo.y(h.value)} r={4.5} fill={h.estimate ? 'var(--bg)' : 'var(--online)'} stroke={h.estimate ? 'var(--online)' : 'var(--bg)'} strokeWidth={2} />
          </g>
        )}
      </svg>
      {h && hover !== null && (
        <div className="tip" style={{ left: `${(geo.x(hover) / W) * 100}%`, top: `${geo.y(h.value)}px`, marginTop: -10 }}>
          {h.date}
          <br />
          <b>{h.estimate ? 'about ' : ''}{fmt(h.value, unit)}</b> {label.toLowerCase()}
          {h.estimate && <> once settled</>}
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
