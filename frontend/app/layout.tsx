import type { Metadata } from 'next'
import Link from 'next/link'
import './globals.css'
import { Nav } from '@/components/Nav'
import { loadData } from '@/lib/data'

export const metadata: Metadata = {
  title: 'Dissident Resonance Index',
  description: 'A daily measure of the online audience of far-right extremism in the United States, set against mainstream media.',
}

const BASE = process.env.DRI_BASE_PATH || ''
const REPO = 'https://github.com/aviad12g/dri-tracker'

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
        <footer className="site-foot">
          <div className="wrap foot-in">
            <div>
              <Link href="/" className="brand">
                <b>DRI</b>
                <span>Dissident Resonance Index</span>
              </Link>
              <p>
                A daily measure of the online audience of far-right extremism in the United States, set against mainstream media. Every
                figure in the index is a recorded public observation or computed from one. The one estimate on the site, Rumble views
                scaled for young uploads, is marked where it appears.
              </p>
            </div>
            <nav className="foot-links" aria-label="More">
              <Link href="/method/">How the index is computed</Link>
              <Link href="/data/">What was read today</Link>
              <Link href="/constituents/">Who is tracked, and why</Link>
              <a href={`${BASE}/data/index.json`}>The full dataset</a>
              <a href={REPO}>Source code</a>
            </nav>
            {data && (
              <dl className="foot-meta">
                <dt>Reading</dt>
                <dd>{data.meta.as_of}</dd>
                <dt>Model</dt>
                <dd>{data.meta.model_version}</dd>
                <dt>Registry</dt>
                <dd>{data.meta.registry_version}</dd>
                <dt>Inputs</dt>
                <dd title={data.meta.input_digest}>SHA-256 {data.meta.input_digest.slice(0, 12)}</dd>
              </dl>
            )}
          </div>
        </footer>
      </body>
    </html>
  )
}
