'use client'

import { useEffect, useState } from 'react'

export default function Home() {
  const [token, setToken] = useState<string | null>(null)
  const [hasToken, setHasToken] = useState(false)

  useEffect(() => {
    const storedToken = sessionStorage.getItem('dev_jwt_token')
    setToken(storedToken)
    setHasToken(!!storedToken)
  }, [])

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Vancelian Core - Dev Frontend</h1>
      
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Status</h2>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${hasToken ? 'bg-green-500' : 'bg-red-500'}`} />
            <span>JWT Token: {hasToken ? 'Present' : 'Not set'}</span>
          </div>
          <div className="text-sm text-gray-600 mt-4">
            <p>This is a DEV-ONLY frontend for testing the Vancelian Core API.</p>
            <p className="mt-2">To get started:</p>
            <ol className="list-decimal list-inside mt-2 space-y-1 ml-4">
              <li>Paste a JWT token in the token bar above</li>
              <li>Navigate to the desired page using the menu</li>
              <li>Test the E2E flows (deposit → compliance → invest)</li>
            </ol>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Available Pages</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="border border-gray-200 rounded p-4">
            <h3 className="font-semibold mb-2">Wallet</h3>
            <p className="text-sm text-gray-600 mb-2">View wallet balances (total, available, blocked, locked)</p>
            <a href="/wallet" className="text-blue-600 text-sm hover:underline">Go to Wallet →</a>
          </div>
          
          <div className="border border-gray-200 rounded p-4">
            <h3 className="font-semibold mb-2">Transactions</h3>
            <p className="text-sm text-gray-600 mb-2">View transaction history</p>
            <a href="/transactions" className="text-blue-600 text-sm hover:underline">Go to Transactions →</a>
          </div>
          
          <div className="border border-gray-200 rounded p-4">
            <h3 className="font-semibold mb-2">Invest</h3>
            <p className="text-sm text-gray-600 mb-2">Create investment intent (lock funds)</p>
            <a href="/invest" className="text-blue-600 text-sm hover:underline">Go to Invest →</a>
          </div>
          
          <div className="border border-gray-200 rounded p-4">
            <h3 className="font-semibold mb-2">Admin / Compliance</h3>
            <p className="text-sm text-gray-600 mb-2">Release or reject deposits (ADMIN/COMPLIANCE/OPS only)</p>
            <a href="/admin/compliance" className="text-blue-600 text-sm hover:underline">Go to Admin →</a>
          </div>
          
          <div className="border border-gray-200 rounded p-4 col-span-2">
            <h3 className="font-semibold mb-2">ZAND Webhook Simulator</h3>
            <p className="text-sm text-gray-600 mb-2">Simulate ZAND bank deposit webhook (generates HMAC signature)</p>
            <a href="/tools/zand-webhook" className="text-blue-600 text-sm hover:underline">Go to ZAND Webhook →</a>
          </div>
        </div>
      </div>
    </div>
  )
}


