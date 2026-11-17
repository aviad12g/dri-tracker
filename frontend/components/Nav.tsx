'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const LINKS = [
  { href: '/', label: 'Reading' },
  { href: '/constituents/', label: 'Who is tracked' },
  { href: '/data/', label: 'Data quality' },
  { href: '/method/', label: 'Method' },
]

export function Nav() {
  const path = usePathname() || '/'
  const here = path.endsWith('/') ? path : `${path}/`
  return (
    <nav className="nav" aria-label="Sections">
      {LINKS.map((l) => (
        <Link key={l.href} href={l.href} aria-current={here === l.href ? 'page' : undefined}>
          {l.label}
        </Link>
      ))}
    </nav>
  )
}
