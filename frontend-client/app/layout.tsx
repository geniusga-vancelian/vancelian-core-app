import type { Metadata } from 'next'
import './globals.css'
import { DevBanner } from '@/components/DevBanner'
import { TopBar } from '@/components/TopBar'

export const metadata: Metadata = {
  title: 'Vancelian Client',
  description: 'Vancelian Core Client Frontend',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <DevBanner />
        <TopBar />
        {children}
      </body>
    </html>
  )
}

