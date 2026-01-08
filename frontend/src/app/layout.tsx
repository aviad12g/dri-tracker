import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/components/Sidebar'
import { Header } from '@/components/Header'

export const metadata: Metadata = {
  title: 'DRI Tracker',
  description: 'Dissident Resonance Index - OSINT Analytics',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="noise">
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <Header />
            <main className="flex-1 overflow-y-auto bg-bg-primary">
              <div className="p-6 max-w-[1600px]">
                {children}
              </div>
            </main>
          </div>
        </div>
      </body>
    </html>
  )
}
