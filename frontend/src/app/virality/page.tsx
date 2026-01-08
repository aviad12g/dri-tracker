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
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { generateMockViralityBreakdown, generateMockDRI } from '@/lib/mockData'

const PLATFORM_COLORS: Record<string, string> = {
  tiktok: '#ff0050',
  youtube: '#ff0000',
  youtube_short: '#ff4444',
  x: '#ffffff',
  instagram: '#e1306c',
  telegram: '#0088cc',
  rumble: '#85c742',
}

const TIER_COLORS: Record<string, string> = {
  mega: '#f59e0b',
  core: '#8b5cf6',
  prop: '#06b6d4',
}

export default function ViralityPage() {
  const [viralityData, setViralityData] = useState<any>(null)
  const [driData, setDriData] = useState<any>(null)
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
    setViralityData(generateMockViralityBreakdown())
    setDriData(generateMockDRI(days))
  }, [timeRange])

  const platformData = useMemo(() => {
    if (!viralityData?.by_platform) return []
    return Object.entries(viralityData.by_platform)
      .map(([platform, value]) => ({
        name: platform.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
        value: value as number,
        color: PLATFORM_COLORS[platform] || '#666',
      }))
      .sort((a, b) => b.value - a.value)
  }, [viralityData])

  const tierData = useMemo(() => {
    if (!viralityData?.by_tier) return []
    return Object.entries(viralityData.by_tier).map(([tier, value]) => ({
      name: tier.charAt(0).toUpperCase() + tier.slice(1),
      value: value as number,
      color: TIER_COLORS[tier] || '#666',
    }))
  }, [viralityData])

  const vScoreData = useMemo(() => {
    if (!driData?.data) return []
    return driData.data.map((d: any) => ({
      date: d.date,
      value: d.v_score,
    }))
  }, [driData])

  const latestV = vScoreData.length ? vScoreData[vScoreData.length - 1].value : 0
  const totalEngagement = platformData.reduce((sum, p) => sum + p.value, 0)

  const formatNumber = (n: number) => {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
    return n.toString()
  }

  if (!mounted || !viralityData) {
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
            V_score Analysis
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-display font-bold text-[#f59e0b] num">
              {latestV.toFixed(1)}
            </span>
            <span className="text-[13px] text-text-tertiary">
              / 100
            </span>
          </div>
        </div>

        {/* Time Range */}
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

      {/* V_score Timeline */}
      <div className="card p-6">
        <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-4">
          V_score over time
        </div>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={vScoreData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="vGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
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
                stroke="#f59e0b"
                strokeWidth={2}
                fill="url(#vGrad)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Platform & Tier Breakdown */}
      <div className="grid grid-cols-12 gap-6">
        {/* By Platform */}
        <div className="col-span-12 lg:col-span-7">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-1">
                  By Platform
                </div>
                <div className="text-[13px] text-text-secondary">
                  {formatNumber(totalEngagement)} total weighted engagement
                </div>
              </div>
            </div>
            <div className="space-y-3">
              {platformData.map((platform, i) => {
                const pct = (platform.value / totalEngagement * 100)
                return (
                  <div key={platform.name} className="animate-slide-up" style={{ animationDelay: `${i * 30}ms` }}>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[12px] text-text-primary">{platform.name}</span>
                      <span className="text-[12px] font-mono text-text-secondary">
                        {formatNumber(platform.value)}
                      </span>
                    </div>
                    <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: platform.color,
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* By Tier */}
        <div className="col-span-12 lg:col-span-5">
          <div className="card p-6 h-full">
            <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-6">
              By Actor Tier
            </div>
            <div className="flex items-center justify-center h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={tierData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {tierData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} stroke="transparent" />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex items-center justify-center gap-6 mt-4">
              {tierData.map((tier) => (
                <div key={tier.name} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: tier.color }} />
                  <span className="text-[11px] text-text-secondary">{tier.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Formula */}
      <div className="card p-5">
        <div className="text-[11px] text-text-quaternary mb-2">Formula</div>
        <div className="font-mono text-[12px] text-text-tertiary">
          V_vir = <span className="text-text-secondary">SUM</span>(W_actor * W_platform * (views + 10*shares) * ln(followers))
        </div>
      </div>
    </div>
  )
}
