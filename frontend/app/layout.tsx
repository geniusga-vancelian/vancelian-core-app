import type { Metadata } from 'next'
import './globals.css'
import { TokenBar } from '@/components/TokenBar'

export const metadata: Metadata = {
  title: 'Vancelian Core - Dev Frontend',
  description: 'DEV-ONLY frontend for local E2E testing',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <div className="bg-red-600 text-white text-center py-2 text-sm font-bold">
          ⚠️ DEV-ONLY FRONTEND - NOT FOR PRODUCTION USE ⚠️
        </div>
        <TokenBar />
        <nav className="bg-white border-b border-gray-200 px-4 py-3">
          <div className="max-w-7xl mx-auto flex gap-4">
            <a href="/" className="text-blue-600 hover:text-blue-800">Home</a>
            <a href="/wallet" className="text-blue-600 hover:text-blue-800">Wallet</a>
            <a href="/transactions" className="text-blue-600 hover:text-blue-800">Transactions</a>
            <a href="/invest" className="text-blue-600 hover:text-blue-800">Invest</a>
            <a href="/admin/compliance" className="text-blue-600 hover:text-blue-800">Admin</a>
            <a href="/tools/zand-webhook" className="text-blue-600 hover:text-blue-800">ZAND Webhook</a>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-8">
          {children}
        </main>
      </body>
    </html>
  )
}

