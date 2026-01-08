'use client'

import { cn, formatPercent, getChangeColor, getTierColor, getTierLabel, getPlatformLabel, getPlatformColor } from '@/lib/utils'
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/react/24/solid'
import type { TopMover } from '@/lib/api'

interface TopMoversTableProps {
  movers: TopMover[]
  limit?: number
}

export function TopMoversTable({ movers, limit = 5 }: TopMoversTableProps) {
  const displayMovers = movers.slice(0, limit)

  return (
    <div className="divide-y divide-terminal-border">
      {displayMovers.map((mover, index) => {
        const change = mover.change_7d ?? mover.change_24h ?? 0
        const platform = mover.platform ?? 'unknown'
        
        return (
          <div
            key={`${mover.actor_id}-${platform}-${index}`}
            className={cn(
              'py-3 flex items-center justify-between hover:bg-terminal-elevated/50 transition-colors -mx-5 px-5',
            )}
          >
            <div className="flex items-center space-x-3">
              {/* Rank indicator */}
              <div 
                className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold"
                style={{
                  backgroundColor: index < 3 ? `${getTierColor(mover.tier)}15` : '#16161d',
                  color: index < 3 ? getTierColor(mover.tier) : '#6b7280',
                }}
              >
                {index + 1}
              </div>

              {/* Actor info */}
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white truncate">
                    {mover.name}
                  </span>
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0"
                    style={{
                      backgroundColor: `${getTierColor(mover.tier)}20`,
                      color: getTierColor(mover.tier),
                    }}
                  >
                    {getTierLabel(mover.tier)}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span 
                    className="text-[10px]"
                    style={{ color: getPlatformColor(platform) }}
                  >
                    {getPlatformLabel(platform)}
                  </span>
                  {mover.engagement_rate != null && (
                    <>
                      <span className="text-terminal-border">|</span>
                      <span className="text-[10px] text-terminal-muted">
                        {mover.engagement_rate.toFixed(1)}% eng
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Change indicator */}
            <div className="text-right shrink-0">
              {change !== 0 ? (
                <div className={cn('flex items-center justify-end gap-1', getChangeColor(change))}>
                  {change > 0 ? (
                    <ArrowTrendingUpIcon className="w-4 h-4" />
                  ) : (
                    <ArrowTrendingDownIcon className="w-4 h-4" />
                  )}
                  <span className="text-sm font-mono font-medium">
                    {formatPercent(change)}
                  </span>
                </div>
              ) : (
                <span className="text-xs text-terminal-muted">--</span>
              )}
              <div className="text-[10px] text-terminal-muted mt-0.5">
                7d change
              </div>
            </div>
          </div>
        )
      })}

      {displayMovers.length === 0 && (
        <div className="py-8 text-center text-terminal-muted text-sm">
          No data available
        </div>
      )}
    </div>
  )
}
