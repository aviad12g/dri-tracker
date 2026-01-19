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
import { generateMockDRI, generateMockTopMovers, generateMockEvents, generateMockAlerts } from '@/lib/mockData'

// Real data type from backend
interface RealTimeData {
  dri: number
  v_score: number
  r_score: number
  s_score: number
  p_score: number
  computed_at: string
  data_quality: string
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
}

export default function OverviewPage() {
  const [data, setData] = useState<any>(null)
  const [realData, setRealData] = useState<RealTimeData | null>(null)
  const [movers, setMovers] = useState<any[]>([])
  const [events, setEvents] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any>(null)
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => {
    setMounted(true)
    
    // Fetch real data from static JSON
    fetch('/data/realtime.json')
      .then(res => res.json())
      .then((real: RealTimeData) => {
        setRealData(real)
        
        // Generate chart data using real current DRI but mock history
        const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
        const mockData = generateMockDRI(days)
        
        // Replace the last data point with real data
        if (mockData.data.length > 0) {
          mockData.data[mockData.data.length - 1] = {
            date: new Date().toISOString().split('T')[0],
            dri: real.dri,
            v_score: real.v_score,
            r_score: real.r_score,
            s_score: real.s_score,
            p_score: real.p_score,
          }
        }
        
        setData(mockData)
        
        // Convert top_actors to movers format
        const realMovers = real.top_actors.slice(0, 5).map((actor, i) => ({
          actor_id: actor.actor_id,
          name: actor.name,
          tier: actor.tier,
          platform: Object.keys(actor.platforms)[0] || 'rumble',
          followers: actor.total_reach,
          change_pct: 0, // No historical data yet
        }))
        setMovers(realMovers)
      })
      .catch(() => {
        // Fall back to mock data if real data fails
        const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
        setData(generateMockDRI(days))
        setMovers(generateMockTopMovers().movers)
      })
    
    setEvents(generateMockEvents(10))
    setAlerts(generateMockAlerts())
  }, [timeRange])

  const latest = useMemo(() => {
    if (!data?.data.length) return null
    return data.data[data.data.length - 1]
  }, [data])

  const previous = useMemo(() => {
    if (!data?.data.length || data.data.length < 2) return null
    return data.data[data.data.length - 2]
  }, [data])

  const change = latest && previous ? ((latest.dri - previous.dri) / previous.dri * 100) : 0

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

  if (!mounted || !data) {
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
                  {realData && (
                    <span className={`text-[9px] px-2 py-0.5 rounded-full font-medium ${
                      realData.data_quality === 'good' ? 'bg-success/20 text-success' :
                      realData.data_quality === 'partial' ? 'bg-warning/20 text-warning' :
                      'bg-text-tertiary/20 text-text-tertiary'
                    }`}>
                      {realData.data_quality === 'good' ? 'LIVE' : realData.data_quality.toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="flex items-baseline gap-3">
                  <span className="text-5xl font-display font-bold text-text-primary num">
                    {realData?.dri.toFixed(1) || latest?.dri.toFixed(1)}
                  </span>
                  <span className={`text-sm font-medium ${change >= 0 ? 'text-success' : 'text-danger'}`}>
                    {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                  </span>
                </div>
                {realData && (
                  <div className="text-[10px] text-text-quaternary mt-1">
                    Updated {new Date(realData.computed_at).toLocaleString()}
                  </div>
                )}
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
                  data={data.data}
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
            const value = realData?.[key as keyof RealTimeData] as number ?? latest?.[key] ?? 0
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
                  Top Actors {realData && <span className="text-success text-[10px] ml-2">LIVE DATA</span>}
                </div>
                <div className="text-[11px] text-text-tertiary">Ranked by weighted influence score</div>
              </div>
              <button className="text-[11px] text-text-tertiary hover:text-text-secondary transition-colors">
                View all
              </button>
            </div>
            <div className="divide-y divide-border">
              {(realData?.top_actors || movers).slice(0, 5).map((actor: any, i: number) => (
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

        {/* Recent Events + Alerts */}
        <div className="col-span-12 lg:col-span-5 space-y-4">
          {/* Alerts */}
          {alerts?.spikes?.length > 0 && (
            <div className="card border-danger/30 bg-danger/5 p-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-danger/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                  </svg>
                </div>
                <div>
                  <div className="text-[13px] font-medium text-danger mb-1">Spike Detected</div>
                  <div className="text-[12px] text-text-secondary">
                    DRI reached {alerts.spikes[0].dri.toFixed(1)} on {format(parseISO(alerts.spikes[0].date), 'MMM d')}
                  </div>
                  <div className="text-[11px] text-text-tertiary mt-1">
                    +{alerts.spikes[0].magnitude.toFixed(1)} standard deviations
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Recent Events */}
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-border">
              <div className="text-[13px] font-medium text-text-primary">Recent Events</div>
              <div className="text-[11px] text-text-tertiary">Political crossover signals</div>
            </div>
            <div className="divide-y divide-border">
              {events.slice(0, 4).map((event) => (
                <div key={event.id} className="px-5 py-3 hover:bg-bg-tertiary transition-colors">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-text-quaternary">
                      {format(parseISO(event.date), 'MMM d')}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent/10 text-accent">
                      +{event.score_delta}
                    </span>
                  </div>
                  <div className="text-[12px] text-text-secondary line-clamp-2">
                    {event.description}
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
