'use client'

import { useState, useEffect, useMemo } from 'react'
import { format, parseISO, subDays } from 'date-fns'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'

// Dashboard data type from backend
interface DashboardData {
  timeseries: Array<{
    date: string
    dri: number
    v_score: number
    r_score: number
    s_score: number
    p_score: number
    is_spike: boolean
    data_quality: string
  }>
  stats: {
    latest: number
    avg_7d: number
    avg_30d: number
    min_90d: number
    max_90d: number
    change_1d: number
    change_7d: number
    change_30d: number
  }
  current: {
    dri: number
    v_score: number
    r_score: number
    s_score: number
    p_score: number
    computed_at: string
    data_quality: string
  }
  top_actors: Array<{
    actor_id: string
    name: string
    tier: string
    faction: string
    total_reach: number
    weighted_score: number
    platforms: Record<string, number>
  }>
  platform_breakdown: Record<string, { total_followers: number; actor_count: number }>
  faction_breakdown: Record<string, { actor_count: number; total_reach: number }>
  alerts: {
    spikes: Array<{ date: string; dri: number }>
    spike_count_30d: number
  }
}

export default function OverviewPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => {
    setMounted(true)
    
    // Fetch complete dashboard data
    fetch('/data/dashboard.json')
      .then(res => res.json())
      .then((data: DashboardData) => {
        setDashboard(data)
      })
      .catch((err) => {
        console.error('Failed to load dashboard data:', err)
      })
  }, [])
  
  // Filter timeseries based on selected range
  const chartData = useMemo(() => {
    if (!dashboard?.timeseries) return []
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
    return dashboard.timeseries.slice(-days)
  }, [dashboard, timeRange])

  const latest = useMemo(() => {
    if (!chartData.length) return null
    return chartData[chartData.length - 1]
  }, [chartData])

  const previous = useMemo(() => {
    if (!chartData.length || chartData.length < 2) return null
    return chartData[chartData.length - 2]
  }, [chartData])

  const change = dashboard?.stats?.change_1d 
    ? (dashboard.stats.change_1d / (dashboard.current.dri - dashboard.stats.change_1d) * 100)
    : (latest && previous ? ((latest.dri - previous.dri) / previous.dri * 100) : 0)

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="bg-bg-elevated border border-border rounded-xl p-4 shadow-card min-w-[200px]">
        <div className="text-[11px] text-text-tertiary mb-3">
          {format(parseISO(d.date), 'EEEE, MMM d')}
        </div>
        <div className="text-3xl font-display font-semibold text-text-primary mb-3">
          {d.dri.toFixed(1)}
        </div>
        <div className="grid grid-cols-2 gap-2">
          {[
            { key: 'v_score', label: 'V', color: '#f59e0b' },
            { key: 'r_score', label: 'R', color: '#8b5cf6' },
            { key: 's_score', label: 'S', color: '#06b6d4' },
            { key: 'p_score', label: 'P', color: '#10b981' },
          ].map(({ key, label, color }) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-[11px]" style={{ color }}>{label}</span>
              <span className="text-[11px] font-mono text-text-secondary">
                {d[key].toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!mounted || !dashboard) {
    return (
      <div className="h-[400px] flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Hero Section */}
      <div className="grid grid-cols-12 gap-6">
        {/* Main DRI Card */}
        <div className="col-span-12 lg:col-span-8">
          <div className="card p-6">
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[11px] text-text-tertiary uppercase tracking-wider">
                    Dissident Resonance Index
                  </span>
                  <span className={`text-[9px] px-2 py-0.5 rounded-full font-medium ${
                    dashboard.current.data_quality === 'good' ? 'bg-success/20 text-success' :
                    dashboard.current.data_quality === 'partial' ? 'bg-warning/20 text-warning' :
                    'bg-text-tertiary/20 text-text-tertiary'
                  }`}>
                    {dashboard.current.data_quality === 'good' ? 'LIVE DATA' : dashboard.current.data_quality.toUpperCase()}
                  </span>
                </div>
                <div className="flex items-baseline gap-3">
                  <span className="text-5xl font-display font-bold text-text-primary num">
                    {dashboard.current.dri.toFixed(1)}
                  </span>
                  <span className={`text-sm font-medium ${change >= 0 ? 'text-success' : 'text-danger'}`}>
                    {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                  </span>
                </div>
                <div className="flex items-center gap-4 mt-2">
                  <div className="text-[10px] text-text-quaternary">
                    7d avg: <span className="text-text-secondary font-mono">{dashboard.stats.avg_7d.toFixed(1)}</span>
                  </div>
                  <div className="text-[10px] text-text-quaternary">
                    30d avg: <span className="text-text-secondary font-mono">{dashboard.stats.avg_30d.toFixed(1)}</span>
                  </div>
                  <div className="text-[10px] text-text-quaternary">
                    Range: <span className="text-text-secondary font-mono">{dashboard.stats.min_90d.toFixed(0)}-{dashboard.stats.max_90d.toFixed(0)}</span>
                  </div>
                </div>
              </div>

              {/* Time Range Selector */}
              <div className="flex items-center gap-1 bg-bg-tertiary rounded-lg p-1">
                {(['7d', '30d', '90d'] as const).map((range) => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range)}
                    className={`px-3 py-1.5 rounded-md text-[12px] font-medium transition-all ${
                      timeRange === range
                        ? 'bg-bg-elevated text-text-primary'
                        : 'text-text-tertiary hover:text-text-secondary'
                    }`}
                  >
                    {range.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {/* Chart */}
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={chartData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid 
                    strokeDasharray="3 3" 
                    stroke="rgba(255,255,255,0.04)" 
                    vertical={false}
                  />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(d) => format(parseISO(d), 'MMM d')}
                    stroke="transparent"
                    tick={{ fill: '#52525b', fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    minTickGap={60}
                  />
                  <YAxis
                    domain={[0, 100]}
                    stroke="transparent"
                    tick={{ fill: '#52525b', fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    width={30}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="dri"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    fill="url(#gradient)"
                    dot={false}
                    activeDot={{
                      r: 4,
                      fill: '#f59e0b',
                      stroke: '#09090b',
                      strokeWidth: 2,
                    }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Subscores */}
        <div className="col-span-12 lg:col-span-4 space-y-4">
          {[
            { key: 'v_score', label: 'Virality', color: '#f59e0b', desc: 'Content spread velocity' },
            { key: 'r_score', label: 'Radicalization', color: '#8b5cf6', desc: 'Funnel conversion depth' },
            { key: 's_score', label: 'Search', color: '#06b6d4', desc: 'Public interest delta' },
            { key: 'p_score', label: 'Political', color: '#10b981', desc: 'Mainstream crossover' },
          ].map(({ key, label, color, desc }, i) => {
            const value = dashboard.current[key as keyof typeof dashboard.current] as number ?? 0
            return (
              <div 
                key={key} 
                className="card p-4 animate-slide-up"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-0.5">
                      {label}
                    </div>
                    <div className="text-[10px] text-text-quaternary">
                      {desc}
                    </div>
                  </div>
                  <div className="text-right">
                    <div 
                      className="text-2xl font-display font-bold num" 
                      style={{ color }}
                    >
                      {value.toFixed(1)}
                    </div>
                  </div>
                </div>
                {/* Mini sparkline bar */}
                <div className="mt-3 h-1 bg-bg-tertiary rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full transition-all duration-500"
                    style={{ 
                      width: `${value}%`, 
                      backgroundColor: color 
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Lower Section */}
      <div className="grid grid-cols-12 gap-6">
        {/* Top Movers */}
        <div className="col-span-12 lg:col-span-7">
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <div>
                <div className="text-[13px] font-medium text-text-primary">
                  Top Actors <span className="text-success text-[10px] ml-2">LIVE DATA</span>
                </div>
                <div className="text-[11px] text-text-tertiary">Ranked by weighted influence score</div>
              </div>
              <div className="text-[10px] text-text-quaternary">
                {dashboard.top_actors.length} tracked
              </div>
            </div>
            <div className="divide-y divide-border">
              {dashboard.top_actors.slice(0, 5).map((actor: any, i: number) => (
                <div 
                  key={actor.actor_id} 
                  className="px-5 py-3 flex items-center justify-between hover:bg-bg-tertiary transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-md bg-bg-tertiary flex items-center justify-center">
                      <span className="text-[10px] font-mono text-text-quaternary">{i + 1}</span>
                    </div>
                    <div>
                      <div className="text-[13px] text-text-primary">{actor.name}</div>
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                          actor.tier === 'mega' ? 'bg-accent/20 text-accent' :
                          actor.tier === 'core' ? 'bg-purple-500/20 text-purple-400' :
                          'bg-cyan-500/20 text-cyan-400'
                        }`}>
                          {actor.tier?.toUpperCase()}
                        </span>
                        <span className="text-[10px] text-text-quaternary capitalize">
                          {actor.faction}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[13px] font-mono font-medium text-text-primary">
                      {(actor.total_reach || actor.followers || 0).toLocaleString()}
                    </div>
                    <div className="text-[10px] text-text-quaternary">
                      {actor.platforms ? Object.keys(actor.platforms).join(', ') : actor.platform}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Stats + Platform Breakdown */}
        <div className="col-span-12 lg:col-span-5 space-y-4">
          {/* Status Card */}
          <div className="card p-4">
            <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-3">
              Data Status
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] text-text-quaternary">Actors Tracked</div>
                <div className="text-xl font-display font-bold text-text-primary">
                  {dashboard.top_actors.length}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-text-quaternary">Spikes (30d)</div>
                <div className="text-xl font-display font-bold text-text-primary">
                  {dashboard.alerts.spike_count_30d}
                </div>
              </div>
            </div>
          </div>

          {/* Platform Breakdown */}
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-border">
              <div className="text-[13px] font-medium text-text-primary">Platform Reach</div>
              <div className="text-[11px] text-text-tertiary">Total followers by platform</div>
            </div>
            <div className="divide-y divide-border">
              {Object.entries(dashboard.platform_breakdown)
                .sort((a, b) => (b[1].total_followers || 0) - (a[1].total_followers || 0))
                .map(([platform, data]) => (
                <div key={platform} className="px-5 py-3 flex items-center justify-between hover:bg-bg-tertiary transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${
                      platform === 'rumble' ? 'bg-green-500' :
                      platform === 'telegram' ? 'bg-blue-500' :
                      platform === 'youtube' ? 'bg-red-500' :
                      'bg-pink-500'
                    }`} />
                    <span className="text-[13px] text-text-primary capitalize">{platform}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-[13px] font-mono text-text-primary">
                      {(data.total_followers || 0).toLocaleString()}
                    </div>
                    <div className="text-[10px] text-text-quaternary">
                      {data.actor_count} actors
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* Faction Breakdown */}
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-border">
              <div className="text-[13px] font-medium text-text-primary">Faction Analysis</div>
              <div className="text-[11px] text-text-tertiary">Movement composition</div>
            </div>
            <div className="divide-y divide-border">
              {Object.entries(dashboard.faction_breakdown)
                .sort((a, b) => (b[1].total_reach || 0) - (a[1].total_reach || 0))
                .map(([faction, data]) => (
                <div key={faction} className="px-5 py-3 flex items-center justify-between hover:bg-bg-tertiary transition-colors">
                  <div>
                    <span className="text-[13px] text-text-primary capitalize">{faction}</span>
                    <span className="text-[10px] text-text-quaternary ml-2">({data.actor_count} actors)</span>
                  </div>
                  <div className="text-[13px] font-mono text-text-primary">
                    {(data.total_reach || 0).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Formula Reference - Minimal */}
      <div className="card p-5">
        <div className="flex items-center gap-6 text-[12px] font-mono text-text-tertiary">
          <span className="text-text-quaternary">DRI =</span>
          <span><span className="text-[#f59e0b]">0.4</span>V</span>
          <span className="text-text-quaternary">+</span>
          <span><span className="text-[#8b5cf6]">0.3</span>R</span>
          <span className="text-text-quaternary">+</span>
          <span><span className="text-[#06b6d4]">0.2</span>S</span>
          <span className="text-text-quaternary">+</span>
          <span><span className="text-[#10b981]">0.1</span>P</span>
        </div>
      </div>
    </div>
  )
}
