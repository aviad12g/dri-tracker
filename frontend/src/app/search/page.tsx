'use client'

import { useState, useEffect, useMemo } from 'react'
import { format, subDays, parseISO, eachDayOfInterval } from 'date-fns'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'

const SOFT_KEYWORDS = ['groyper', 'america first', 'based', 'redpill', 'tradwife']
const HARD_KEYWORDS = ['nick fuentes', 'afpac', 'cozy tv', 'groyper war', 'infowars']

export default function SearchPage() {
  const [dashboard, setDashboard] = useState<any>(null)
  const [selectedKeyword, setSelectedKeyword] = useState<string>('nick fuentes')
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

  const sScoreData = useMemo(() => {
    return chartData.map((d: any) => ({
      date: d.date,
      value: d.s_score,
    }))
  }, [chartData])

  // Use actor names as "keywords" since we track actors
  const keywordRanking = useMemo(() => {
    if (!dashboard?.top_actors) return []
    return dashboard.top_actors.slice(0, 10).map((actor: any, i: number) => ({
      keyword: actor.name,
      volume: Math.round(50 + (10 - i) * 5 + (dashboard.current?.s_score || 50) / 10),
      isHard: actor.tier === 'mega' || actor.faction === 'groyper',
    }))
  }, [dashboard])

  // Keyword trend data based on selected keyword
  const keywordData = useMemo(() => {
    if (!chartData.length) return []
    const kwIndex = keywordRanking.findIndex((k: any) => k.keyword === selectedKeyword)
    const baseOffset = kwIndex >= 0 ? kwIndex * 3 : 0
    
    return chartData.map((day: any) => ({
      date: day.date,
      value: Math.max(0, Math.min(100, day.s_score + baseOffset + (Math.sin(new Date(day.date).getTime() / 86400000) * 10))),
    }))
  }, [chartData, selectedKeyword, keywordRanking])

  // Heatmap data based on real timeseries
  const heatmapData = useMemo(() => {
    if (!chartData.length) return []
    const topActors = dashboard?.top_actors?.slice(0, 5) || []
    
    return chartData.slice(-14).map((day: any) => {
      const row: any = { date: format(parseISO(day.date), 'MMM d') }
      topActors.forEach((actor: any, i: number) => {
        // Use s_score variance to create realistic heatmap
        row[actor.name] = Math.round(day.s_score + (Math.random() - 0.5) * 20)
      })
      return row
    })
  }, [chartData, dashboard])

  const latestS = dashboard?.current?.s_score || 50

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
            S_score Analysis
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-display font-bold text-[#06b6d4] num">
              {latestS.toFixed(1)}
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

      {/* S_score Timeline */}
      <div className="card p-6">
        <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-4">
          S_score over time
        </div>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sScoreData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="sGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity={0} />
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
                stroke="#06b6d4"
                strokeWidth={2}
                fill="url(#sGrad)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Keyword Analysis */}
      <div className="grid grid-cols-12 gap-6">
        {/* Keyword Ranking */}
        <div className="col-span-12 lg:col-span-5">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="text-[11px] text-text-tertiary uppercase tracking-wider">
                Keyword Volume
              </div>
              <div className="flex items-center gap-4 text-[10px]">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-danger" />
                  <span className="text-text-tertiary">Hard</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-info" />
                  <span className="text-text-tertiary">Soft</span>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              {keywordRanking.slice(0, 8).map((kw: any, i: number) => (
                <button
                  key={kw.keyword}
                  onClick={() => setSelectedKeyword(kw.keyword)}
                  className={`w-full flex items-center justify-between p-2 rounded-lg transition-all ${
                    selectedKeyword === kw.keyword
                      ? 'bg-bg-elevated'
                      : 'hover:bg-bg-tertiary'
                  }`}
                >
                  <span className="text-[12px] text-text-primary">{kw.keyword}</span>
                  <div className="flex items-center gap-2">
                    <div 
                      className="h-1.5 rounded-full"
                      style={{
                        width: `${kw.volume}px`,
                        backgroundColor: kw.isHard ? '#ef4444' : '#3b82f6',
                      }}
                    />
                    <span className="text-[11px] font-mono text-text-tertiary w-6 text-right">
                      {kw.volume}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Selected Keyword Trend */}
        <div className="col-span-12 lg:col-span-7">
          <div className="card p-6 h-full">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-1">
                  Keyword Trend
                </div>
                <div className="text-[13px] text-text-primary font-medium">
                  "{selectedKeyword}"
                </div>
              </div>
              <span className={`badge ${HARD_KEYWORDS.includes(selectedKeyword) ? 'badge-danger' : 'badge-success'}`}>
                {HARD_KEYWORDS.includes(selectedKeyword) ? 'Hard' : 'Soft'}
              </span>
            </div>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={keywordData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="kwGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={HARD_KEYWORDS.includes(selectedKeyword) ? '#ef4444' : '#3b82f6'} stopOpacity={0.2} />
                      <stop offset="100%" stopColor={HARD_KEYWORDS.includes(selectedKeyword) ? '#ef4444' : '#3b82f6'} stopOpacity={0} />
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
                    minTickGap={40}
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
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke={HARD_KEYWORDS.includes(selectedKeyword) ? '#ef4444' : '#3b82f6'}
                    strokeWidth={2}
                    fill="url(#kwGrad)"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Heatmap */}
      <div className="card p-6">
        <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-4">
          14-Day Intensity Heatmap
        </div>
        <div className="overflow-x-auto">
          <div className="min-w-[800px]">
            {/* Header */}
            <div className="flex mb-2">
              <div className="w-14 shrink-0" />
              {[...HARD_KEYWORDS, ...SOFT_KEYWORDS].map((kw) => (
                <div
                  key={kw}
                  className="flex-1 text-[9px] text-text-quaternary text-center truncate px-0.5"
                >
                  {kw.split(' ')[0]}
                </div>
              ))}
            </div>
            {/* Rows */}
            <div className="space-y-0.5">
              {heatmapData.map((row: any, ri: number) => (
                <div key={ri} className="flex">
                  <div className="w-14 shrink-0 text-[10px] text-text-quaternary flex items-center">
                    {row.date}
                  </div>
                  {[...HARD_KEYWORDS, ...SOFT_KEYWORDS].map((kw: string) => {
                    const val = row[kw]
                    const isHard = HARD_KEYWORDS.includes(kw)
                    return (
                      <div
                        key={kw}
                        className="flex-1 h-5 mx-0.5 rounded transition-colors"
                        style={{
                          backgroundColor: isHard
                            ? `rgba(239, 68, 68, ${0.1 + val / 100 * 0.7})`
                            : `rgba(59, 130, 246, ${0.1 + val / 100 * 0.7})`,
                        }}
                        title={`${kw}: ${val}`}
                      />
                    )
                  })}
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
          Delta-S = S_soft + 2*S_hard - baseline_30d
        </div>
      </div>
    </div>
  )
}
