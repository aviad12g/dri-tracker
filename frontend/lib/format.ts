const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

export function longDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  return `${d} ${MONTHS[m - 1]} ${y}`
}

export function shortDate(iso: string): string {
  const [, m, d] = iso.split('-').map(Number)
  return `${d} ${MONTHS[m - 1].slice(0, 3)}`
}

export function compact(n: number | null | undefined): string {
  if (n === null || n === undefined) return 'n/a'
  const a = Math.abs(n)
  if (a >= 1e9) return `${(n / 1e9).toFixed(2)}B`
  if (a >= 1e6) return `${(n / 1e6).toFixed(a >= 1e7 ? 1 : 2)}M`
  if (a >= 1e4) return `${(n / 1e3).toFixed(0)}K`
  if (a >= 1e3) return `${(n / 1e3).toFixed(1)}K`
  return `${Math.round(n)}`
}

export function whole(n: number): string {
  return Math.round(n).toLocaleString('en-US')
}

export function pct(x: number | null | undefined, digits = 0): string {
  if (x === null || x === undefined) return 'n/a'
  return `${(x * 100).toFixed(digits)}%`
}

export function signedPct(x: number | null | undefined, digits = 0): string {
  if (x === null || x === undefined) return 'n/a'
  const v = x * 100
  return `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(digits)}%`
}

export function signed(x: number, digits = 1): string {
  return `${x > 0 ? '+' : x < 0 ? '−' : ''}${Math.abs(x).toFixed(digits)}`
}

export const PLATFORM_NAME: Record<string, string> = {
  youtube: 'YouTube',
  telegram: 'Telegram',
  rumble: 'Rumble',
  bitchute: 'BitChute',
  x: 'X',
  apple_podcasts: 'Apple Podcasts',
  wikipedia: 'Wikipedia',
  gdelt: 'GDELT news',
  adl_heat: 'ADL H.E.A.T. Map',
}

export const COHORT_NAME: Record<string, string> = {
  white_nationalist: 'White nationalist',
  antisemitic_conspiracy: 'Antisemitic conspiracy',
  neo_nazi: 'Neo-Nazi',
  militia: 'Militia and street groups',
  conspiracy: 'Conspiracy media',
  male_supremacy: 'Male supremacy',
  mainstream_amplifier: 'Mainstream amplifier',
  reference: 'Reference',
}

/** One plain sentence for a pillar's raw statistic. */
export function rawSentence(id: string, raw: number | null, detail: Record<string, any>): string {
  if (raw === null) return ''
  switch (id) {
    case 'reach':
      return `${pct(raw, 1)} of the combined audience`
    case 'engagement':
      return `${pct(raw, 1)} of combined weekly views`
    case 'mainstreaming':
      return `${pct(raw, 1)} of podcast-chart points`
    case 'momentum':
      return `${signedPct(detail.annual_change, 0)} audience a year`
    case 'breadth':
      return `${detail.growing} of ${detail.accounts} accounts growing`
    case 'heat':
      return `${raw.toFixed(2)} times its yearly norm`
    case 'depth':
      return `${pct(raw, 0)} of the way to unmoderated`
    default:
      return ''
  }
}
