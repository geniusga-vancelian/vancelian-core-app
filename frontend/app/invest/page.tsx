'use client'

import { useState } from 'react'
import { investmentsApi, ApiError } from '@/lib/api'

export default function InvestPage() {
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<any>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [formData, setFormData] = useState({
    amount: '',
    currency: 'AED',
    offer_id: '',
    reason: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const data = await investmentsApi.create(formData)
      setResponse(data)
      setFormData({ amount: '', currency: 'AED', offer_id: '', reason: '' })
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

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Create Investment</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Amount *
            </label>
            <input
              type="text"
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              required
              placeholder="1000.00"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Currency *
            </label>
            <select
              value={formData.currency}
              onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="AED">AED</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Offer ID *
            </label>
            <input
              type="text"
              value={formData.offer_id}
              onChange={(e) => setFormData({ ...formData, offer_id: e.target.value })}
              required
              placeholder="uuid"
              className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Reason *
            </label>
            <textarea
              value={formData.reason}
              onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
              required
              placeholder="Investment reason..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              rows={3}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Creating...' : 'Create Investment'}
          </button>
        </form>
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

      {response && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="text-green-800 font-semibold">Success</div>
          <div className="text-green-600 text-sm mt-2">
            <div>Transaction ID: <span className="font-mono">{response.transaction_id}</span></div>
            <div className="mt-1">Status: <span className="font-semibold">{response.status}</span></div>
          </div>
        </div>
      )}
    </div>
  )
}


