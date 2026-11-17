/** The index scale: a ruled 0-100 line with the reading's needle and its robustness band, edges labelled. */
export function Ruler({ score, band }: { score: number | null; band: { low: number; high: number } | null }) {
  const label =
    score === null
      ? 'No reading published'
      : `Index reading ${score.toFixed(1)} on a scale of 0 to 100` +
        (band ? `, between ${band.low.toFixed(1)} and ${band.high.toFixed(1)} under alternative assumptions` : '')
  const showBand = band !== null && score !== null
  return (
    <div className="ruler" role="img" aria-label={label}>
      {showBand && (
        <>
          <div className="ruler-band" style={{ left: `${band.low}%`, width: `${Math.max(band.high - band.low, 0.3)}%` }} />
          <span className="ruler-edge lo" style={{ left: `${band.low}%` }} aria-hidden="true">{band.low.toFixed(1)}</span>
          <span className="ruler-edge hi" style={{ left: `${band.high}%` }} aria-hidden="true">{band.high.toFixed(1)}</span>
        </>
      )}
      <div className="ruler-ticks" />
      {score !== null && <div className="ruler-needle" style={{ left: `${score}%` }} />}
      <div className="ruler-labels" aria-hidden="true">
        {[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100].map((t) => (
          <span key={t} style={{ left: `${t}%` }}>
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}
