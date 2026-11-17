import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'
import { Nav } from '@/components/Nav'
import { loadData } from '@/lib/data'

export const metadata: Metadata = {
  title: 'Dissident Resonance Index',
  description: 'A deterministic index of the online reach of US far-right extremist media, built from recorded public observations.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const data = loadData()
  return (
    <html lang="en">
      <body>
        <header className="mast">
          <div className="wrap mast-in">
            <Link href="/" className="brand">
              <b>DRI</b>
              <span>Dissident Resonance Index</span>
            </Link>
            <Nav />
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="wrap footer">
          <span>
            Every figure on this site is a recorded public observation or computed from one. Nothing is simulated or estimated.
          </span>
          {data && (
            <span>
              Model {data.meta.model_version}, registry {data.meta.registry_version}
            </span>
          )}
        </footer>
      </body>
    </html>
  )
}
