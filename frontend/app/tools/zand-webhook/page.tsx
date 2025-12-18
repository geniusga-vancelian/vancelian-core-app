'use client'

import { useState } from 'react'
import { webhooksApi, ApiError } from '@/lib/api'

export default function ZandWebhookPage() {
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<any>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [formData, setFormData] = useState({
    provider_event_id: '',
    iban: 'AE123456789012345678901',
    user_id: '',
    amount: '',
    currency: 'AED',
    occurred_at: new Date().toISOString(),
  })

  const webhookSecret = process.env.NEXT_PUBLIC_ZAND_WEBHOOK_SECRET || ''

  const generateHMAC = async (payload: string): Promise<string> => {
    if (!webhookSecret) {
      throw new Error('NEXT_PUBLIC_ZAND_WEBHOOK_SECRET not set')
    }
    // Use Web Crypto API for HMAC in browser (dev-only)
    const encoder = new TextEncoder()
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(webhookSecret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    )
    const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(payload))
    const hashArray = Array.from(new Uint8Array(signature))
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const payload = JSON.stringify(formData)
      const signature = await generateHMAC(payload)
      const timestamp = Math.floor(Date.now() / 1000).toString()

      const data = await webhooksApi.zandDeposit(formData, signature, timestamp)
      setResponse(data)
      // Generate new provider_event_id for next request
      setFormData({ ...formData, provider_event_id: globalThis.crypto.randomUUID() })
    } catch (err: any) {
      setError(err as ApiError)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">ZAND Webhook Simulator</h1>

      {!webhookSecret && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-6">
          <div className="text-yellow-800 font-semibold">Warning</div>
          <div className="text-yellow-600 text-sm mt-1">
            NEXT_PUBLIC_ZAND_WEBHOOK_SECRET is not set. Webhook signature will fail.
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Provider Event ID *
            </label>
            <input
              type="text"
              value={formData.provider_event_id}
              onChange={(e) => setFormData({ ...formData, provider_event_id: e.target.value })}
              required
              placeholder="unique-event-id"
              className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
            />
            <button
              type="button"
              onClick={() => setFormData({ ...formData, provider_event_id: globalThis.crypto.randomUUID() })}
              className="mt-1 text-xs text-blue-600 hover:underline"
            >
              Generate UUID
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              IBAN *
            </label>
            <input
              type="text"
              value={formData.iban}
              onChange={(e) => setFormData({ ...formData, iban: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              User ID (UUID) *
            </label>
            <input
              type="text"
              value={formData.user_id}
              onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
              required
              placeholder="uuid"
              className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
            />
          </div>

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
              Occurred At *
            </label>
            <input
              type="datetime-local"
              value={new Date(formData.occurred_at).toISOString().slice(0, 16)}
              onChange={(e) => setFormData({ ...formData, occurred_at: new Date(e.target.value).toISOString() })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !webhookSecret}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Sending...' : 'Send Webhook'}
          </button>
        </form>
      </div>

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

      {response && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="text-green-800 font-semibold">Success</div>
          <div className="text-green-600 text-sm mt-2 space-y-1">
            <div>Status: <span className="font-semibold">{response.status}</span></div>
            <div>Transaction ID: <span className="font-mono">{response.transaction_id}</span></div>
            {response.trace_id && (
              <div>Trace ID: <span className="font-mono">{response.trace_id}</span></div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
