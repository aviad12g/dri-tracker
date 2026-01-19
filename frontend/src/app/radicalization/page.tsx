'use client'

import { useState, useEffect, useMemo } from 'react'
import { format, parseISO } from 'date-fns'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from 'recharts'

export default function RadicalizationPage() {
  const [dashboard, setDashboard] = useState<any>(null)
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    fetch('/data/dashboard.json')
      .then(res => res.json())
      .then(data => setDashboard(data))
      .catch(err => console.error('Failed to load data:', err))
  }, [])

  const chartData = useMemo(() => {
    if (!dashboard?.timeseries) return []
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
    return dashboard.timeseries.slice(-days)
  }, [dashboard, timeRange])

  const rScoreData = useMemo(() => {
    return chartData.map((d: any) => ({
      date: d.date,
      value: d.r_score,
    }))
  }, [chartData])

  const latestR = dashboard?.current?.r_score || 0
  const avgR = rScoreData.length ? rScoreData.reduce((s: number, d: any) => s + d.value, 0) / rScoreData.length : 0

  // Calculate funnel from platform breakdown (mainstream vs alt-tech)
  const platformBreakdown = dashboard?.platform_breakdown || {}
  const mainstreamReach = (platformBreakdown.youtube?.total_followers || 0) + (platformBreakdown.tiktok?.total_followers || 0)
  const altTechReach = (platformBreakdown.rumble?.total_followers || 0) + (platformBreakdown.telegram?.total_followers || 0)
  
  const latestFunnel = {
    discovery: mainstreamReach,
    indoctrination: Math.round((mainstreamReach + altTechReach) / 2),
    mobilization: altTechReach,
  }

  const conversionRate = latestFunnel.discovery > 0 
    ? (latestFunnel.mobilization / latestFunnel.discovery * 100).toFixed(1)
    : '0'

  const formatNumber = (n: number) => {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
    return n.toString()
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
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-1">
            R_score Analysis
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-display font-bold text-[#8b5cf6] num">
              {latestR.toFixed(1)}
            </span>
            <span className="text-[13px] text-text-tertiary">
              / 100
            </span>
          </div>
        </div>

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

      {/* Funnel Visualization */}
      <div className="card p-6">
        <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-6">
          Audience Funnel
        </div>
        <div className="flex items-center justify-center gap-2 md:gap-8">
          {/* Discovery */}
          <div className="flex-1 max-w-[200px]">
            <div className="aspect-square relative">
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-blue-500/20 to-blue-500/5 border border-blue-500/20 flex flex-col items-center justify-center">
                <span className="text-2xl font-display font-bold text-blue-400">
                  {formatNumber(latestFunnel.discovery)}
                </span>
                <span className="text-[10px] text-text-tertiary mt-1">Discovery</span>
              </div>
            </div>
          </div>

          {/* Arrow */}
          <svg className="w-8 h-8 text-text-quaternary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>

          {/* Indoctrination */}
          <div className="flex-1 max-w-[160px]">
            <div className="aspect-square relative">
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-purple-500/20 to-purple-500/5 border border-purple-500/20 flex flex-col items-center justify-center">
                <span className="text-2xl font-display font-bold text-purple-400">
                  {formatNumber(latestFunnel.indoctrination)}
                </span>
                <span className="text-[10px] text-text-tertiary mt-1">Indoctrination</span>
              </div>
            </div>
          </div>

          {/* Arrow */}
          <svg className="w-8 h-8 text-text-quaternary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>

          {/* Mobilization */}
          <div className="flex-1 max-w-[120px]">
            <div className="aspect-square relative">
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-b from-red-500/20 to-red-500/5 border border-red-500/20 flex flex-col items-center justify-center">
                <span className="text-xl font-display font-bold text-red-400">
                  {formatNumber(latestFunnel.mobilization)}
                </span>
                <span className="text-[10px] text-text-tertiary mt-1">Mobilization</span>
              </div>
            </div>
          </div>
        </div>

        {/* Conversion Rate */}
        <div className="mt-6 pt-6 border-t border-border flex items-center justify-center gap-8">
          <div className="text-center">
            <div className="text-[10px] text-text-quaternary uppercase tracking-wider mb-1">
              Conversion Rate
            </div>
            <div className="text-xl font-mono font-semibold text-[#8b5cf6]">
              {conversionRate}%
            </div>
          </div>
        </div>
      </div>

      {/* R_score Timeline */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="text-[11px] text-text-tertiary uppercase tracking-wider">
            R_score over time
          </div>
          <div className="text-[11px] text-text-quaternary">
            Avg: {avgR.toFixed(1)}
          </div>
        </div>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={rScoreData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="rGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
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
              <ReferenceLine y={avgR} stroke="#8b5cf6" strokeDasharray="3 3" strokeOpacity={0.5} />
              <Tooltip
                contentStyle={{
                  background: '#18181b',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '12px',
                  padding: '12px',
                }}
                labelFormatter={(d) => format(parseISO(d as string), 'MMM d, yyyy')}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#8b5cf6"
                strokeWidth={2}
                fill="url(#rGrad)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Discovery', value: formatNumber(latestFunnel.discovery), desc: 'X, TikTok impressions', color: '#3b82f6' },
          { label: 'Indoctrination', value: formatNumber(latestFunnel.indoctrination), desc: 'YouTube, Podcasts', color: '#8b5cf6' },
          { label: 'Mobilization', value: formatNumber(latestFunnel.mobilization), desc: 'Telegram, Rumble', color: '#ef4444' },
        ].map((stat, i) => (
          <div key={stat.label} className="card p-4 animate-slide-up" style={{ animationDelay: `${i * 50}ms` }}>
            <div className="text-[10px] text-text-quaternary uppercase tracking-wider mb-1">
              {stat.label}
            </div>
            <div className="text-2xl font-display font-bold num" style={{ color: stat.color }}>
              {stat.value}
            </div>
            <div className="text-[10px] text-text-tertiary mt-1">
              {stat.desc}
            </div>
          </div>
        ))}
      </div>

      {/* Formula */}
      <div className="card p-5">
        <div className="text-[11px] text-text-quaternary mb-2">Formula</div>
        <div className="font-mono text-[12px] text-text-tertiary">
          R_rad = (telegram + rumble) / x_feeder * 100
        </div>
      </div>
    </div>
  )
}
