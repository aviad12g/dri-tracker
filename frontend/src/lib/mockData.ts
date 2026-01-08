/**
 * Mock data for development when backend is not available.
 * This allows the UI to render with realistic-looking data.
 */

import { format, subDays } from 'date-fns'

// Generate dates for the last N days
function generateDates(days: number): string[] {
  const dates: string[] = []
  for (let i = days - 1; i >= 0; i--) {
    dates.push(format(subDays(new Date(), i), 'yyyy-MM-dd'))
  }
  return dates
}

// Generate a random value with trend and noise
function generateValue(base: number, day: number, trend: number = 0.1, noise: number = 0.1): number {
  const trendValue = base + (day * trend)
  const noiseValue = (Math.random() - 0.5) * noise * base * 2
  return Math.max(0, trendValue + noiseValue)
}

// Generate DRI timeseries
export function generateMockDRI(days: number = 90) {
  const dates = generateDates(days)
  const spikeDays = [Math.floor(days * 0.17), Math.floor(days * 0.5), Math.floor(days * 0.83)]
  
  const data = dates.map((date, i) => {
    const isSpike = spikeDays.includes(i)
    const spikeMultiplier = isSpike ? 1.3 : 1
    
    const v_score = Math.min(100, Math.max(0, generateValue(52, i, 0.05, 0.15) * spikeMultiplier))
    const r_score = Math.min(100, Math.max(0, generateValue(48, i, 0.03, 0.12)))
    const s_score = Math.min(100, Math.max(0, generateValue(45, i, 0.02, 0.2) * spikeMultiplier))
    const p_score = Math.min(100, Math.max(0, generateValue(30, i, 0.01, 0.25)))
    
    const dri = 0.4 * v_score + 0.3 * r_score + 0.2 * s_score + 0.1 * p_score
    
    return {
      date,
      dri: Math.round(dri * 100) / 100,
      v_score: Math.round(v_score * 100) / 100,
      r_score: Math.round(r_score * 100) / 100,
      s_score: Math.round(s_score * 100) / 100,
      p_score: Math.round(p_score * 100) / 100,
      is_spike: isSpike,
      data_quality: isSpike ? 'partial' : 'verified',
    }
  })
  
  const latest = data[data.length - 1]
  const prev = data[data.length - 2]
  const last7 = data.slice(-7)
  const last30 = data.slice(-30)
  
  return {
    data,
    stats: {
      latest: latest.dri,
      avg_7d: last7.reduce((sum, d) => sum + d.dri, 0) / 7,
      avg_30d: last30.reduce((sum, d) => sum + d.dri, 0) / 30,
      change_1d: latest.dri - prev.dri,
      pct_change_1d: ((latest.dri - prev.dri) / prev.dri) * 100,
    },
  }
}

// Mock actors
export const mockActors = [
  {
    actor_id: 'fuentes_nick',
    name: 'Nick Fuentes',
    tier: 'mega',
    x_handle: 'NickJFuentes',
    youtube_channel_id: 'UC123fake',
    telegram_channel_username: 'nickjfuentes',
    notes: 'America First movement leader',
  },
  {
    actor_id: 'milo_y',
    name: 'Milo Yiannopoulos',
    tier: 'core',
    x_handle: 'nero',
    notes: 'Former Breitbart editor',
  },
  {
    actor_id: 'baked_alaska',
    name: 'Baked Alaska',
    tier: 'prop',
    x_handle: 'baborama',
    notes: 'Streamer',
  },
  {
    actor_id: 'shapiro_ben',
    name: 'Ben Shapiro',
    tier: 'control',
    x_handle: 'benshapiro',
    youtube_channel_id: 'UCnQC_G5Xsjhp9fEJKuIcrSw',
    notes: 'Daily Wire - control benchmark',
  },
  {
    actor_id: 'walsh_matt',
    name: 'Matt Walsh',
    tier: 'control',
    x_handle: 'MattWalshBlog',
    youtube_channel_id: 'UCO3fXmMfY5S5b38FLqoIYCw',
    notes: 'Daily Wire - control benchmark',
  },
]

// Mock top movers
export function generateMockTopMovers() {
  return {
    movers: [
      { actor_id: 'fuentes_nick', name: 'Nick Fuentes', tier: 'mega', change_7d: 45.2, engagement_rate: 8.5, platform: 'x' },
      { actor_id: 'baked_alaska', name: 'Baked Alaska', tier: 'prop', change_7d: 32.1, engagement_rate: 12.3, platform: 'youtube' },
      { actor_id: 'milo_y', name: 'Milo Yiannopoulos', tier: 'core', change_7d: 28.7, engagement_rate: 6.2, platform: 'telegram' },
      { actor_id: 'vincent_james', name: 'Vincent James', tier: 'prop', change_7d: 18.5, engagement_rate: 5.1, platform: 'rumble' },
      { actor_id: 'beardson', name: 'Beardson Beardly', tier: 'core', change_7d: 15.2, engagement_rate: 9.8, platform: 'cozy' },
      { actor_id: 'ethan_ralph', name: 'Ethan Ralph', tier: 'prop', change_7d: -5.3, engagement_rate: 4.1, platform: 'rumble' },
      { actor_id: 'catboy_kami', name: 'Catboy Kami', tier: 'prop', change_7d: -12.4, engagement_rate: 3.8, platform: 'telegram' },
    ],
  }
}

// Mock political events
export function generateMockEvents(count: number = 20) {
  const categories = ['media', 'political', 'rally', 'legal']
  const descriptions = [
    { category: 'media', texts: [
      'Movement slogan mentioned in mainstream news coverage',
      'Viral clip featured on national broadcast',
      'Podcast interview with mainstream host',
      'Op-ed published in major publication',
      'Documentary feature released',
    ]},
    { category: 'political', texts: [
      'Public meeting with congressional candidate',
      'State legislator quoted movement rhetoric',
      'Campaign rally appearance',
      'Policy document echoes movement language',
      'Political endorsement received',
    ]},
    { category: 'rally', texts: [
      'Large public rally organized',
      'Counter-protest at university event',
      'Flash mob demonstration',
      'Conference speaking engagement',
      'Community meetup with high attendance',
    ]},
    { category: 'legal', texts: [
      'Lawsuit filed related to deplatforming',
      'Court appearance for related charges',
      'Investigation announced by authorities',
      'Settlement reached in civil case',
      'Appeals court ruling received',
    ]},
  ]

  const events = []
  for (let i = 0; i < count; i++) {
    const category = categories[Math.floor(Math.random() * categories.length)]
    const catDesc = descriptions.find(d => d.category === category)!
    const description = catDesc.texts[Math.floor(Math.random() * catDesc.texts.length)]
    
    events.push({
      id: String(i + 1),
      date: format(subDays(new Date(), Math.floor(Math.random() * 90)), 'yyyy-MM-dd'),
      category,
      actor_id: Math.random() > 0.5 ? mockActors[Math.floor(Math.random() * 3)].actor_id : null,
      description,
      score_delta: Math.floor(Math.random() * 4) + 1,
      evidence_url: `https://example.com/event${i + 1}`,
      created_at: new Date().toISOString(),
    })
  }
  
  return events.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
}

// Mock search interest data
export function generateMockSearchData(days: number = 30) {
  const dates = generateDates(days)
  const keywords = [
    'nick fuentes',
    'groyper',
    'america first',
    'afpac',
    'cozy tv',
    'redpill',
    'tradwife',
    'based',
    'groyper war',
    'infowars',
  ]
  
  const byKeyword: Record<string, Array<{ date: string; value: number }>> = {}
  
  keywords.forEach((keyword, ki) => {
    byKeyword[keyword] = dates.map((date, di) => ({
      date,
      value: Math.round(generateValue(30 + ki * 3, di, 0.3, 0.4)),
    }))
  })
  
  return {
    region: 'US',
    keywords: keywords.map(k => ({
      keyword: k,
      data: byKeyword[k],
    })),
    byKeyword,
  }
}

// Mock search interest heatmap data
export function generateMockSearchHeatmap() {
  const dates = generateDates(30)
  const keywords = [
    'great replacement',
    'white genocide',
    'groyper',
    'america first',
    'anti-white',
    'immigration crisis',
    'border security',
    'christian nationalism',
  ]
  
  const keywordData: Record<string, Array<{ date: string; value: number }>> = {}
  
  keywords.forEach((keyword, ki) => {
    keywordData[keyword] = dates.map((date, di) => ({
      date,
      value: Math.round(generateValue(30 + ki * 5, di, 0.2, 0.3)),
    }))
  })
  
  return {
    region: 'US',
    keywords: keywordData,
  }
}

// Mock alerts
export function generateMockAlerts() {
  return {
    spikes: [
      {
        date: format(subDays(new Date(), 3), 'yyyy-MM-dd'),
        dri: 67.4,
        z_score: 2.3,
        direction: 'up',
        magnitude: 2.3,
      },
      {
        date: format(subDays(new Date(), 12), 'yyyy-MM-dd'),
        dri: 71.2,
        z_score: 2.8,
        direction: 'up',
        magnitude: 2.8,
      },
    ],
    recent_events: generateMockEvents(5),
  }
}

// Mock virality breakdown
export function generateMockViralityBreakdown() {
  return {
    by_platform: {
      tiktok: 450000 + Math.floor(Math.random() * 100000),
      youtube: 320000 + Math.floor(Math.random() * 80000),
      youtube_short: 280000 + Math.floor(Math.random() * 60000),
      x: 180000 + Math.floor(Math.random() * 40000),
      instagram: 95000 + Math.floor(Math.random() * 20000),
      telegram: 75000 + Math.floor(Math.random() * 15000),
      rumble: 45000 + Math.floor(Math.random() * 10000),
    },
    by_tier: {
      mega: 650000 + Math.floor(Math.random() * 100000),
      core: 420000 + Math.floor(Math.random() * 80000),
      prop: 278000 + Math.floor(Math.random() * 50000),
    },
    share_velocity: [],
  }
}

// Mock funnel data
export function generateMockFunnelData(days: number = 30) {
  const dates = generateDates(days)
  
  return {
    daily: dates.map((date, i) => ({
      date,
      discovery: Math.floor(generateValue(2000000, i, 5000, 0.1)),
      indoctrination: Math.floor(generateValue(350000, i, 2000, 0.15)),
      mobilization: Math.floor(generateValue(45000, i, 500, 0.2)),
    })),
  }
}

// Mock radicalization breakdown
export function generateMockRadicalizationBreakdown() {
  return {
    telegram_views: 75000 + Math.floor(Math.random() * 10000),
    rumble_concurrents: 4500 + Math.floor(Math.random() * 1000),
    x_feeder_impressions: 2100000 + Math.floor(Math.random() * 300000),
    r_rad: 3.79 + (Math.random() - 0.5) * 0.5,
    funnel_ratio: 0.038 + (Math.random() - 0.5) * 0.01,
  }
}
