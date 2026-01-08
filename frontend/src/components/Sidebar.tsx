'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navigation = [
  { 
    name: 'Overview', 
    href: '/', 
    shortcut: 'O',
  },
  { 
    name: 'Virality', 
    href: '/virality', 
    shortcut: 'V',
  },
  { 
    name: 'Radicalization', 
    href: '/radicalization', 
    shortcut: 'R',
  },
  { 
    name: 'Search', 
    href: '/search', 
    shortcut: 'S',
  },
  { 
    name: 'Events', 
    href: '/events', 
    shortcut: 'E',
  },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-[240px] h-screen flex flex-col bg-bg-secondary border-r border-border">
      {/* Logo */}
      <div className="h-14 flex items-center px-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center">
            <span className="text-black text-xs font-bold font-display">D</span>
          </div>
          <div>
            <span className="text-sm font-semibold text-text-primary font-display tracking-tight">
              DRI Tracker
            </span>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3">
        <div className="space-y-0.5">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`
                  group flex items-center justify-between px-3 py-2 rounded-lg text-[13px] font-medium
                  transition-all duration-150 ease-out
                  ${isActive 
                    ? 'bg-bg-elevated text-text-primary' 
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
                  }
                `}
              >
                <span>{item.name}</span>
                <span className={`
                  text-[10px] font-mono px-1.5 py-0.5 rounded
                  transition-all duration-150
                  ${isActive 
                    ? 'bg-accent/20 text-accent' 
                    : 'bg-bg-tertiary text-text-quaternary group-hover:text-text-tertiary'
                  }
                `}>
                  {item.shortcut}
                </span>
              </Link>
            )
          })}
        </div>

        {/* Divider */}
        <div className="my-4 h-px bg-border" />

        {/* Quick Actions */}
        <div className="space-y-0.5">
          <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] text-text-tertiary hover:text-text-secondary hover:bg-bg-tertiary transition-all duration-150">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            <span>Upload CSV</span>
          </button>
          <button className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] text-text-tertiary hover:text-text-secondary hover:bg-bg-tertiary transition-all duration-150">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span>Settings</span>
          </button>
        </div>
      </nav>

      {/* Status Footer */}
      <div className="p-3 border-t border-border">
        <div className="px-3 py-2.5 rounded-lg bg-bg-tertiary">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-soft" />
              <span className="text-[11px] text-text-secondary">Live</span>
            </div>
            <span className="text-[10px] text-text-quaternary font-mono">v1.0.0</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
