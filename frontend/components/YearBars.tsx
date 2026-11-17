import { whole } from '@/lib/format'

function niceMax(v: number): number {
  const mag = Math.pow(10, Math.floor(Math.log10(Math.max(v, 1))))
  for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * mag >= v) return m * mag
  return 10 * mag
}

/** One count per year as columns. The peak and the latest year are labelled; the rest show on hover or focus. */
export function YearBars({ years, label }: { years: { year: number; count: number }[]; label: string }) {
  if (!years.length) return null
  const peak = Math.max(...years.map((y) => y.count))
  const max = niceMax(peak)
  const last = years[years.length - 1]
  const peakYear = years.find((y) => y.count === peak)!.year
  return (
    <div className="ybars" role="img"
      aria-label={`${label} by year, ${years[0].year} to ${last.year}. ${whole(last.count)} in ${last.year}; the most was ${whole(peak)} in ${peakYear}.`}>
      <div className="ybars-plot">
        {years.map((y) => (
          <div className={`ycol${y.year === last.year || y.year === peakYear ? ' on' : ''}`} key={y.year} tabIndex={0}>
            <span className="yval">{whole(y.count)}</span>
            <i style={{ height: `${Math.max((y.count / max) * 100, y.count > 0 ? 1 : 0)}%` }} />
          </div>
        ))}
      </div>
      <div className="ybars-axis">
        {years.map((y, i) => (
          <span key={y.year}>{(years.length - 1 - i) % 2 === 0 ? y.year : ''}</span>
        ))}
      </div>
    </div>
  )
}
