import fs from 'node:fs'
import path from 'node:path'

export type Pillar = {
  id: string
  label: string
  group: 'scale' | 'dynamics' | 'structure'
  weight: number
  score: number | null
  raw: number | null
  coverage: number
  available: boolean
  reason: string | null
  headline: string
  explain: string
  contribution: number | null
  detail: Record<string, any>
  history: { date: string; score: number }[]
}

export type Account = {
  platform: string
  handle: string
  followers: number | null
  as_of: string | null
  views_7d: number | null
  annual_growth: number | null
  growth_days: number | null
  unverified: boolean
}

export type Constituent = {
  id: string
  name: string
  kind: string
  basket: 'extremism' | 'reference'
  tier: 'core' | 'adjacent' | 'reference'
  cohort: string
  weight: number
  basis: { org: string; url: string }[]
  accounts: Account[]
  audience: number
  basket_share: number | null
  wiki_daily: number | null
  news_7d: number | null
  charts: { chart: string; show: string; rank: number }[]
  wikipedia: string[]
}

export type HeatPoint = { date: string; value: number; baseline: number; ratio: number }

export type Source = {
  source: string
  rows: number
  first: string | null
  last: string | null
  ok: number | null
  failed: { entity: string; account: string; reason: string }[]
  skipped: string | null
  note: string | null
}

/** One upload week of a Rumble channel. Views are to date; `adjusted` scales a young week to maturity. */
export type RumbleWeek = {
  date: string
  views: number
  videos: number
  age: number
  maturity?: number
  adjusted?: number
  adjusted_low?: number
  adjusted_high?: number
  baseline?: number
  baseline_low?: number
  baseline_high?: number
  baseline_weeks?: number
  vs_baseline?: number
  vs_baseline_low?: number
  vs_baseline_high?: number
  status?: 'above' | 'below' | 'usual' | 'no uploads'
}

export type OfflineSeries = {
  id: string
  label: string
  note: string
  total: number
  last: string
  years: { year: number; count: number }[]
  partial: { year: number; count: number; through: string } | null
}
export type Offline = { source: string; url: string; first_year: number; last: string; series: OfflineSeries[] }

export type Dataset = {
  meta: {
    model_version: string
    registry_version: string
    as_of: string
    first_scored: string | null
    days_scored: number
    input_digest: string
    last_run: string | null
    counts: Record<string, number>
    rules: Record<string, string>
  }
  headline: {
    score: number | null
    grade: string | null
    confidence: number
    weight_coverage: number
    pillars_used: string[]
    band: { low: number; high: number } | null
    change: { d1: number | null; d7: number | null; d28: number | null }
  }
  pillars: Pillar[]
  series: { date: string; score: number; confidence: number }[]
  heat_series: { wikipedia: HeatPoint[]; news: HeatPoint[] }
  rumble_view_gains: { id: string; name: string; from: string; to: string; days: number; gained: number; per_week: number }[]
  rumble_upload_weeks: { id: string; name: string; tier: string; captured: string; total: number; weeks: RumbleWeek[]; latest: RumbleWeek | null }[]
  rumble_maturity: {
    method: 'cross-section' | 'longitudinal'
    settled_age: number
    factors: { age: number; m: number; low: number; high: number; n: number }[]
    reference_ages: [number, number]
    horizon: number
    baseline_weeks: number
    baseline_min_weeks: number
    baseline_range: [number, number]
    captures: number
  }
  offline: Offline | null
  constituents: Constituent[]
  platforms: {
    platform: string
    depth: number
    view_equiv: number
    registered: number
    observed: number
    extremism_followers: number
    reference_followers: number
  }[]
  sensitivity: { scenario: string; group: string; score: number | null }[]
  sources: Source[]
  params: Record<string, any>
}

let cached: Dataset | null = null

/** The dataset is read once at build time; the site is fully static. */
export function loadData(): Dataset | null {
  if (cached) return cached
  const file = path.join(process.cwd(), 'public', 'data', 'index.json')
  if (!fs.existsSync(file)) return null
  cached = JSON.parse(fs.readFileSync(file, 'utf8')) as Dataset
  return cached
}
