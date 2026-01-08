/**
 * API client for DRI Tracker backend.
 */

const API_BASE = '/api'

interface FetchOptions {
  method?: string
  body?: any
  headers?: Record<string, string>
}

async function fetchAPI<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options
  
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  
  return res.json()
}

// Types
export interface DRIDailyData {
  date: string
  dri: number
  v_score: number
  r_score: number
  s_score: number
  p_score: number
  is_spike: boolean
  data_quality: string
}

export interface DRITimeseriesResponse {
  data: DRIDailyData[]
  stats: {
    latest?: number
    avg_7d?: number
    avg_30d?: number
    change_1d?: number
    pct_change_1d?: number
  }
}

export interface DRIDetailResponse {
  date: string
  v_vir: number | null
  r_rad: number | null
  delta_s: number | null
  pol: number | null
  v_score: number | null
  r_score: number | null
  s_score: number | null
  p_score: number | null
  dri: number | null
  data_quality_summary: Record<string, any>
  is_spike: boolean
  spike_details: Record<string, any> | null
}

export interface Actor {
  actor_id: string
  name: string
  tier: string
  x_handle?: string
  youtube_channel_id?: string
  telegram_channel_username?: string
  notes?: string
}

export interface ActorTimeseries {
  actor_id: string
  name: string
  tier: string
  data: Array<{
    date: string
    platform: string
    followers: number | null
    views_total: number | null
    shares_total: number | null
    likes_total: number | null
    comments_total: number | null
  }>
}

export interface TopMover {
  actor_id: string
  name: string
  tier: string
  change_24h?: number | null
  change_7d?: number | null
  engagement_rate?: number | null
  platform?: string
}

export interface PoliticalEvent {
  id: string
  date: string
  actor_id: string | null
  category?: string
  description: string
  score_delta: number
  evidence_url?: string | null
  created_at?: string
}

export interface SearchInterest {
  date: string
  keyword: string
  region: string
  volume_index: number
}

export interface SpikeAlert {
  date: string
  dri: number
  z_score: number
  direction: string
  magnitude: number
}

export interface AlertsResponse {
  spikes: SpikeAlert[]
  recent_events: PoliticalEvent[]
}

export interface ViralityBreakdown {
  by_platform: Record<string, number>
  by_tier: Record<string, number>
  share_velocity: any[]
}

export interface RadicalizationBreakdown {
  telegram_views: number
  rumble_concurrents: number
  x_feeder_impressions: number
  r_rad: number
  funnel_ratio: number
}

// API Functions
export async function getDRITimeseries(
  start?: string,
  end?: string
): Promise<DRITimeseriesResponse> {
  const params = new URLSearchParams()
  if (start) params.set('start', start)
  if (end) params.set('end', end)
  const query = params.toString()
  return fetchAPI(`/dri${query ? `?${query}` : ''}`)
}

export async function getDRIComponents(date: string): Promise<DRIDetailResponse> {
  return fetchAPI(`/dri/components?date=${date}`)
}

export async function getViralityBreakdown(date: string): Promise<ViralityBreakdown> {
  return fetchAPI(`/dri/virality?date=${date}`)
}

export async function getRadicalizationBreakdown(date: string): Promise<RadicalizationBreakdown> {
  return fetchAPI(`/dri/radicalization?date=${date}`)
}

export async function getActors(tier?: string): Promise<Actor[]> {
  const query = tier ? `?tier=${tier}` : ''
  return fetchAPI(`/actors${query}`)
}

export async function getActorTimeseries(
  actorId: string,
  start?: string,
  end?: string
): Promise<ActorTimeseries> {
  const params = new URLSearchParams()
  if (start) params.set('start', start)
  if (end) params.set('end', end)
  const query = params.toString()
  return fetchAPI(`/actors/timeseries/${actorId}${query ? `?${query}` : ''}`)
}

export async function getTopMovers(limit = 10): Promise<{ movers: TopMover[] }> {
  return fetchAPI(`/actors/top-movers?limit=${limit}`)
}

export async function getSearchInterest(
  keyword?: string,
  region?: string,
  start?: string,
  end?: string
): Promise<SearchInterest[]> {
  const params = new URLSearchParams()
  if (keyword) params.set('keyword', keyword)
  if (region) params.set('region', region)
  if (start) params.set('start', start)
  if (end) params.set('end', end)
  const query = params.toString()
  return fetchAPI(`/search${query ? `?${query}` : ''}`)
}

export async function getSearchHeatmap(
  region: string,
  start?: string,
  end?: string
): Promise<{ region: string; keywords: Record<string, Array<{ date: string; value: number }>> }> {
  const params = new URLSearchParams({ region })
  if (start) params.set('start', start)
  if (end) params.set('end', end)
  return fetchAPI(`/search/heatmap?${params}`)
}

export async function getPoliticalEvents(
  start?: string,
  end?: string
): Promise<PoliticalEvent[]> {
  const params = new URLSearchParams()
  if (start) params.set('start', start)
  if (end) params.set('end', end)
  const query = params.toString()
  return fetchAPI(`/events${query ? `?${query}` : ''}`)
}

export async function createPoliticalEvent(
  event: Omit<PoliticalEvent, 'id' | 'created_at'>,
  adminPassword: string
): Promise<PoliticalEvent> {
  return fetchAPI('/events', {
    method: 'POST',
    body: event,
    headers: {
      'X-Admin-Password': adminPassword,
    },
  })
}

export async function getAlerts(days = 7): Promise<AlertsResponse> {
  return fetchAPI(`/alerts?days=${days}`)
}

export async function getDataQuality(date: string): Promise<{
  date: string
  overall_quality: string
  coverage_by_platform: Record<string, number>
  missing_metrics: string[]
  source_types: Record<string, string>
}> {
  return fetchAPI(`/quality/${date}`)
}

export async function getHealthCheck(): Promise<{
  status: string
  version: string
  timestamp: string
}> {
  return fetchAPI('/health')
}

