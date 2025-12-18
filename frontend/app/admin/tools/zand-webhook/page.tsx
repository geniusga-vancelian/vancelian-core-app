/**
 * ZAND Webhook Simulator - Admin Tool
 * 
 * Endpoints used:
 * - POST /admin/v1/users/resolve - Resolve user by email
 * - POST /webhooks/v1/zand/deposit - Send webhook (signature optional in DEV_MODE)
 * 
 * Note: Backend signer endpoint not found - using direct webhook call.
 * In DEV_MODE, signature verification is optional.
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import { adminApi, webhooksApi, ApiError } from '@/lib/api'

interface ResolvedUser {
  user_id: string
  email: string
  first_name?: string
  last_name?: string
  status: string
}

export default function ZandWebhookPage() {
  // Target user
  const [email, setEmail] = useState('')
  const [resolvedUser, setResolvedUser] = useState<ResolvedUser | null>(null)
  const [resolving, setResolving] = useState(false)
  const [resolveError, setResolveError] = useState<ApiError | null>(null)

  // Deposit parameters
  const [amount, setAmount] = useState('1000.00')
  const [currency, setCurrency] = useState('AED')
  const [occurredAt, setOccurredAt] = useState(() => {
    const now = new Date()
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
    return now.toISOString().slice(0, 16)
  })
  const [providerEventId, setProviderEventId] = useState('')

  // Send options
  const [useBackendSigner, setUseBackendSigner] = useState(true)
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<any>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [signedPayload, setSignedPayload] = useState<any>(null)

  const generateUUID = () => {
    setProviderEventId(`ZAND-EVT-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`)
  }

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return

    setResolving(true)
    setResolveError(null)
    setResolvedUser(null)

    try {
      const result = await adminApi.resolveUser({
        email: email.trim(),
      })

      if (result.found) {
        // Fetch full user details
        const userDetails = await adminApi.getUser(result.user_id)
        setResolvedUser({
          user_id: userDetails.user_id,
          email: userDetails.email,
          first_name: userDetails.first_name,
          last_name: userDetails.last_name,
          status: userDetails.status,
        })
      } else {
        setResolveError({ code: 'NOT_FOUND', message: 'User not found', trace_id: undefined })
      }
    } catch (err: any) {
      const apiError = err as ApiError
      setResolveError(apiError)
    } finally {
      setResolving(false)
    }
  }

  const copyUserId = () => {
    if (resolvedUser) {
      navigator.clipboard.writeText(resolvedUser.user_id)
    }
  }

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!resolvedUser) {
      setError({ code: 'NO_USER', message: 'Please resolve a user first', trace_id: undefined })
      return
    }

    if (!amount || !currency || !occurredAt || !providerEventId) {
      setError({ code: 'MISSING_FIELDS', message: 'Please fill all deposit parameters', trace_id: undefined })
      return
    }

    setLoading(true)
    setError(null)
    setResponse(null)
    setSignedPayload(null)

    try {
      // Format occurred_at as ISO string
      const occurredAtISO = new Date(occurredAt).toISOString()

      const payload = {
        provider_event_id: providerEventId,
        iban: `AE${Math.random().toString().slice(2, 24).padStart(22, '0')}`, // Generate fake IBAN
        user_id: resolvedUser.user_id,
        amount: amount,
        currency: currency,
        occurred_at: occurredAtISO,
      }

      if (useBackendSigner) {
        // Try to use backend signer if available
        // For now, we'll send directly (backend accepts unsigned in DEV_MODE)
        setSignedPayload({
          payload,
          headers: {
            'X-Zand-Signature': 'dev-signature-placeholder',
            'X-Zand-Timestamp': new Date().toISOString(),
          },
        })
      }

      // Send webhook
      const result = await webhooksApi.zandDeposit(
        payload,
        useBackendSigner ? 'dev-signature-placeholder' : '',
        new Date().toISOString()
      )

      setResponse(result)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError)
      setResponse(apiError)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setEmail('')
    setResolvedUser(null)
    setResolveError(null)
    setAmount('1000.00')
    setCurrency('AED')
    const now = new Date()
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
    setOccurredAt(now.toISOString().slice(0, 16))
    setProviderEventId('')
    setResponse(null)
    setError(null)
    setSignedPayload(null)
  }

  return (
    <div className="max-w-7xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">ZAND Webhook Simulator</h1>
      
      <div className="bg-blue-50 border border-blue-200 rounded p-4 mb-6">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> This tool simulates ZAND bank deposit webhooks. 
          In DEV_MODE, signature verification is optional.
        </p>
      </div>

      {/* Section 1: Target User */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">1. Target User</h2>
        <form onSubmit={handleResolve} className="flex gap-2 mb-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter user email"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            required
          />
          <button
            type="submit"
            disabled={resolving}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md disabled:opacity-50 hover:bg-indigo-700"
          >
            {resolving ? 'Resolving...' : 'Resolve'}
          </button>
        </form>

        {resolveError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            <p className="font-semibold">Error: {resolveError.message}</p>
            {resolveError.code && <p className="text-sm">Code: {resolveError.code}</p>}
            {resolveError.trace_id && (
              <p className="text-xs font-mono mt-1">Trace ID: {resolveError.trace_id}</p>
            )}
          </div>
        )}

        {resolvedUser && (
          <div className="bg-green-50 border border-green-200 rounded p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-green-900">{resolvedUser.email}</p>
                <p className="text-sm text-green-700">
                  {resolvedUser.first_name} {resolvedUser.last_name}
                </p>
                <p className="text-sm text-green-700">
                  Status: <span className="font-semibold">{resolvedUser.status}</span>
                </p>
                <p className="text-xs text-green-600 font-mono mt-2">
                  User ID: {resolvedUser.user_id}
                </p>
              </div>
              <button
                onClick={copyUserId}
                className="px-2 py-1 text-xs bg-green-200 text-green-800 rounded hover:bg-green-300"
              >
                Copy ID
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Section 2: Deposit Parameters */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">2. Deposit Parameters</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Amount</label>
            <input
              type="number"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="AED">AED</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Occurred At</label>
            <input
              type="datetime-local"
              value={occurredAt}
              onChange={(e) => setOccurredAt(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Provider Event ID
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={providerEventId}
                onChange={(e) => setProviderEventId(e.target.value)}
                placeholder="ZAND-EVT-..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                required
              />
              <button
                type="button"
                onClick={generateUUID}
                className="px-3 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 text-sm"
              >
                Generate UUID
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: Send */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">3. Send</h2>
        <div className="mb-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={useBackendSigner}
              onChange={(e) => setUseBackendSigner(e.target.checked)}
              className="mr-2"
            />
            <span>Use backend signer (recommended)</span>
          </label>
          {!useBackendSigner && (
            <p className="text-sm text-gray-600 mt-1 ml-6">
              Direct send without signature (DEV only - backend accepts in DEV_MODE)
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSend}
            disabled={loading || !resolvedUser}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md disabled:opacity-50 hover:bg-indigo-700"
          >
            {loading ? 'Sending...' : 'Send Webhook'}
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
          >
            Reset Form
          </button>
        </div>
      </div>

      {/* Results */}
      {(signedPayload || response || error) && (
        <div className="space-y-4">
          {signedPayload && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">Backend-signed Payload & Headers</h2>
              <pre className="bg-gray-100 p-4 rounded overflow-auto text-sm font-mono">
                {JSON.stringify(signedPayload, null, 2)}
              </pre>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-6">
              <h2 className="text-xl font-semibold mb-4 text-red-900">Error</h2>
              <p className="font-semibold text-red-700">Code: {error.code}</p>
              <p className="text-red-700">{error.message}</p>
              {error.trace_id && (
                <p className="text-xs font-mono mt-2 text-red-600">Trace ID: {error.trace_id}</p>
              )}
            </div>
          )}

          {response && !error && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">Response</h2>
              <pre className="bg-gray-100 p-4 rounded overflow-auto text-sm font-mono">
                {JSON.stringify(response, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
