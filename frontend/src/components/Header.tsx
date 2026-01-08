'use client'

import { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { format } from 'date-fns'

const PAGE_META: Record<string, string> = {
  '/': 'Overview',
  '/virality': 'Virality',
  '/radicalization': 'Radicalization',
  '/search': 'Search',
  '/events': 'Events',
}

export function Header() {
  const pathname = usePathname()
  const [time, setTime] = useState<string>('')
  
  useEffect(() => {
    const updateTime = () => setTime(format(new Date(), 'HH:mm:ss'))
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  const title = PAGE_META[pathname] || 'Dashboard'

  return (
    <header className="h-14 flex items-center justify-between px-6 border-b border-border bg-bg-secondary">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-[13px]">
        <span className="text-text-quaternary">DRI</span>
        <span className="text-text-quaternary">/</span>
        <span className="text-text-primary font-medium">{title}</span>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Time */}
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-soft" />
          <span className="text-[12px] font-mono text-text-tertiary">{time}</span>
        </div>

        {/* Divider */}
        <div className="w-px h-4 bg-border" />

        {/* Actions */}
        <div className="flex items-center gap-1">
          <button className="p-2 rounded-lg text-text-tertiary hover:text-text-secondary hover:bg-bg-tertiary transition-all">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
          </button>
          <button className="p-2 rounded-lg text-text-tertiary hover:text-text-secondary hover:bg-bg-tertiary transition-all relative">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
            </svg>
            <div className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-danger" />
          </button>
        </div>
      </div>
    </header>
  )
}
