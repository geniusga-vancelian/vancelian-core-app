'use client'

import { useState, useEffect } from 'react'
import { walletApi, ApiError } from '@/lib/api'

export default function WalletPage() {
  const [loading, setLoading] = useState(false)
  const [balance, setBalance] = useState<any>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [currency, setCurrency] = useState('AED')

  const fetchBalance = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await walletApi.getBalance(currency)
      setBalance(data)
    } catch (err: any) {
      setError(err as ApiError)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBalance()
  }, [currency])

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Wallet Balance</h1>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Currency:
        </label>
        <select
          value={currency}
          onChange={(e) => setCurrency(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md"
        >
          <option value="AED">AED</option>
        </select>
      </div>

      <button
        onClick={fetchBalance}
        disabled={loading}
        className="mb-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
      >
        {loading ? 'Loading...' : 'Refresh'}
      </button>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
          <div className="text-red-800 font-semibold">Error</div>
          <div className="text-red-600 text-sm mt-1">{error.message}</div>
          {error.code && (
            <div className="text-red-500 text-xs mt-1">Code: {error.code}</div>
          )}
          {error.trace_id && (
            <div className="text-red-500 text-xs mt-1">Trace ID: {error.trace_id}</div>
          )}
        </div>
      )}

      {balance && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Balance ({balance.currency})</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="border border-gray-200 rounded p-4">
              <div className="text-sm text-gray-600">Total Balance</div>
              <div className="text-2xl font-bold mt-1">{balance.total_balance}</div>
            </div>
            <div className="border border-gray-200 rounded p-4">
              <div className="text-sm text-gray-600">Available Balance</div>
              <div className="text-2xl font-bold mt-1 text-green-600">{balance.available_balance}</div>
            </div>
            <div className="border border-gray-200 rounded p-4">
              <div className="text-sm text-gray-600">Blocked Balance</div>
              <div className="text-2xl font-bold mt-1 text-yellow-600">{balance.blocked_balance}</div>
            </div>
            <div className="border border-gray-200 rounded p-4">
              <div className="text-sm text-gray-600">Locked Balance</div>
              <div className="text-2xl font-bold mt-1 text-blue-600">{balance.locked_balance}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

