'use client'

import { useState, useEffect } from 'react'
import { transactionsApi, ApiError } from '@/lib/api'

export default function TransactionsPage() {
  const [loading, setLoading] = useState(false)
  const [transactions, setTransactions] = useState<any[]>([])
  const [error, setError] = useState<ApiError | null>(null)
  const [type, setType] = useState('')
  const [status, setStatus] = useState('')

  const fetchTransactions = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await transactionsApi.list(type || undefined, status || undefined)
      setTransactions(data)
    } catch (err: any) {
      // Enhanced error handling - show network/CORS issues more clearly
      if (err instanceof TypeError && err.message === 'Failed to fetch') {
        const networkError: ApiError = {
          code: 'NETWORK_ERROR',
          message: 'Failed to fetch - Likely CORS issue or backend is down. Check: 1) Backend is running on http://localhost:8000, 2) CORS_ALLOW_ORIGINS includes http://localhost:3000, 3) Browser console for CORS errors',
          details: { originalError: err.message },
        }
        setError(networkError)
      } else {
        setError(err as ApiError)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTransactions()
  }, [])

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Transactions</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Type:
            </label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All</option>
              <option value="DEPOSIT">DEPOSIT</option>
              <option value="INVESTMENT">INVESTMENT</option>
              <option value="WITHDRAWAL">WITHDRAWAL</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status:
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All</option>
              <option value="INITIATED">INITIATED</option>
              <option value="COMPLIANCE_REVIEW">COMPLIANCE_REVIEW</option>
              <option value="AVAILABLE">AVAILABLE</option>
              <option value="LOCKED">LOCKED</option>
              <option value="FAILED">FAILED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={fetchTransactions}
              disabled={loading}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading ? 'Loading...' : 'Filter'}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4">
          <div className="text-red-800 font-semibold">Error {error.code && `(${error.code})`}</div>
          <div className="text-red-600 text-sm mt-1">{error.message}</div>
          {error.trace_id && (
            <div className="text-red-500 text-xs mt-1 font-mono">Trace ID: {error.trace_id}</div>
          )}
          {error.details && (
            <div className="text-red-500 text-xs mt-1">Details: {JSON.stringify(error.details)}</div>
          )}
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Transaction ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Currency</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created At</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                  {loading ? 'Loading...' : 'No transactions found'}
                </td>
              </tr>
            ) : (
              transactions.map((tx) => (
                <tr key={tx.transaction_id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">{tx.transaction_id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{tx.type}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 rounded text-xs ${
                      tx.status === 'AVAILABLE' ? 'bg-green-100 text-green-800' :
                      tx.status === 'LOCKED' ? 'bg-blue-100 text-blue-800' :
                      tx.status === 'COMPLIANCE_REVIEW' ? 'bg-yellow-100 text-yellow-800' :
                      tx.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {tx.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold">{tx.amount}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{tx.currency}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{new Date(tx.created_at).toLocaleString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}


