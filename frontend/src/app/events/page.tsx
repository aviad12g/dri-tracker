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
} from 'recharts'
import { generateMockEvents, generateMockDRI } from '@/lib/mockData'

const CATEGORIES = [
  { id: 'media', label: 'Media', color: '#3b82f6' },
  { id: 'political', label: 'Political', color: '#10b981' },
  { id: 'rally', label: 'Rally', color: '#f59e0b' },
  { id: 'legal', label: 'Legal', color: '#ef4444' },
]

export default function EventsPage() {
  const [events, setEvents] = useState<any[]>([])
  const [driData, setDriData] = useState<any>(null)
  const [filter, setFilter] = useState<string | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [timeRange, setTimeRange] = useState<'30d' | '90d' | '1y'>('90d')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const days = timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 365
    setEvents(generateMockEvents(30))
    setDriData(generateMockDRI(days))
  }, [timeRange])

  const filteredEvents = useMemo(() => {
    let result = events
    if (filter) result = events.filter((e) => e.category === filter)
    return result.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  }, [events, filter])

  const pScoreData = useMemo(() => {
    if (!driData?.data) return []
    return driData.data.map((d: any) => ({
      date: d.date,
      value: d.p_score,
    }))
  }, [driData])

  const latestP = pScoreData.length ? pScoreData[pScoreData.length - 1].value : 0

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    CATEGORIES.forEach((c) => { counts[c.id] = 0 })
    events.forEach((e) => {
      if (counts[e.category] !== undefined) counts[e.category]++
    })
    return counts
  }, [events])

  const totalImpact = events.reduce((sum, e) => sum + e.score_delta, 0)

  if (!mounted || !driData) {
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
            P_score Analysis
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-4xl font-display font-bold text-[#10b981] num">
              {latestP.toFixed(1)}
            </span>
            <span className="text-[13px] text-text-tertiary">
              / 100
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddModal(true)}
            className="btn btn-primary"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Log Event
          </button>
          <div className="flex items-center gap-1 bg-bg-tertiary rounded-lg p-1">
            {(['30d', '90d', '1y'] as const).map((range) => (
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
      </div>

      {/* P_score Timeline */}
      <div className="card p-6">
        <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-4">
          P_score over time
        </div>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={pScoreData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="pGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
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
                stroke="#10b981"
                strokeWidth={2}
                fill="url(#pGrad)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Categories + Events */}
      <div className="grid grid-cols-12 gap-6">
        {/* Category Filter */}
        <div className="col-span-12 lg:col-span-4 space-y-3">
          <div className="text-[11px] text-text-tertiary uppercase tracking-wider mb-2">
            Categories
          </div>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setFilter(filter === cat.id ? null : cat.id)}
              className={`w-full flex items-center justify-between p-3 rounded-xl transition-all ${
                filter === cat.id
                  ? 'bg-bg-elevated border border-border'
                  : 'bg-bg-secondary border border-transparent hover:border-border'
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: cat.color }}
                />
                <span className="text-[13px] text-text-primary">{cat.label}</span>
              </div>
              <span className="text-[12px] font-mono text-text-tertiary">
                {categoryCounts[cat.id]}
              </span>
            </button>
          ))}

          {/* Stats */}
          <div className="card p-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] text-text-quaternary uppercase tracking-wider mb-1">
                  Total Events
                </div>
                <div className="text-xl font-display font-bold text-text-primary num">
                  {events.length}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-text-quaternary uppercase tracking-wider mb-1">
                  Total Impact
                </div>
                <div className="text-xl font-display font-bold text-[#10b981] num">
                  +{totalImpact}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Event List */}
        <div className="col-span-12 lg:col-span-8">
          <div className="card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center justify-between">
              <div className="text-[13px] font-medium text-text-primary">
                Event Log
              </div>
              {filter && (
                <button
                  onClick={() => setFilter(null)}
                  className="text-[11px] text-text-tertiary hover:text-text-secondary transition-colors"
                >
                  Clear filter
                </button>
              )}
            </div>
            <div className="divide-y divide-border max-h-[400px] overflow-y-auto">
              {filteredEvents.slice(0, 15).map((event) => {
                const cat = CATEGORIES.find((c) => c.id === event.category)
                return (
                  <div
                    key={event.id}
                    className="px-5 py-4 hover:bg-bg-tertiary transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] text-text-quaternary">
                            {format(parseISO(event.date), 'MMM d, yyyy')}
                          </span>
                          <span
                            className="text-[9px] px-1.5 py-0.5 rounded uppercase tracking-wider"
                            style={{
                              backgroundColor: `${cat?.color}20`,
                              color: cat?.color,
                            }}
                          >
                            {event.category}
                          </span>
                        </div>
                        <p className="text-[13px] text-text-primary line-clamp-2">
                          {event.description}
                        </p>
                      </div>
                      <div
                        className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center font-mono text-[12px] font-semibold"
                        style={{
                          backgroundColor: `${cat?.color}15`,
                          color: cat?.color,
                        }}
                      >
                        +{event.score_delta}
                      </div>
                    </div>
                  </div>
                )
              })}
              {filteredEvents.length === 0 && (
                <div className="px-5 py-12 text-center text-text-tertiary text-[13px]">
                  No events found
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add Event Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md mx-4 bg-bg-secondary border border-border rounded-2xl shadow-card animate-scale-in">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <span className="text-[15px] font-semibold text-text-primary">Log Event</span>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-lg text-text-tertiary hover:text-text-secondary hover:bg-bg-tertiary transition-all"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-[11px] text-text-tertiary uppercase tracking-wider mb-2">
                  Date
                </label>
                <input
                  type="date"
                  className="input"
                  defaultValue={format(new Date(), 'yyyy-MM-dd')}
                />
              </div>
              <div>
                <label className="block text-[11px] text-text-tertiary uppercase tracking-wider mb-2">
                  Category
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {CATEGORIES.map((cat) => (
                    <button
                      key={cat.id}
                      className="p-3 rounded-xl bg-bg-tertiary border border-border hover:border-border-strong transition-all text-center"
                    >
                      <div
                        className="w-3 h-3 rounded-full mx-auto mb-1"
                        style={{ backgroundColor: cat.color }}
                      />
                      <span className="text-[10px] text-text-secondary">{cat.label}</span>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-[11px] text-text-tertiary uppercase tracking-wider mb-2">
                  Description
                </label>
                <textarea
                  className="input h-24 resize-none"
                  placeholder="Describe the event..."
                />
              </div>
              <div>
                <label className="block text-[11px] text-text-tertiary uppercase tracking-wider mb-2">
                  Impact Score (1-5)
                </label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      className="flex-1 py-2 rounded-lg bg-bg-tertiary border border-border text-[13px] text-text-secondary hover:border-accent hover:text-accent transition-all"
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-3 px-6 py-4 border-t border-border">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 btn btn-primary"
              >
                Log Event
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
