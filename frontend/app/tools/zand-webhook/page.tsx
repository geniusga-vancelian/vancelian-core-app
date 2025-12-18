'use client'

import { useState, useEffect } from 'react'
import { webhooksApi, ApiError } from '@/lib/api'

interface JWTClaims {
  sub?: string
  email?: string
  roles?: string[]
  [key: string]: any
}

/**
 * Decode JWT token and extract claims
 * DEV-ONLY: No signature verification
 */
function decodeJWT(token: string): JWTClaims | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) {
      return null
    }
    const payload = parts[1]
    const decodedPayload = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decodedPayload)
  } catch {
    return null
  }
}

/**
 * Get JWT subject (sub) from sessionStorage
 */
function getJWTSubject(): string | null {
  if (typeof window === 'undefined') return null
  const token = sessionStorage.getItem('dev_jwt_token')
  if (!token) return null
  const claims = decodeJWT(token)
  return claims?.sub || null
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

export default function ZandWebhookPage() {
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<any>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [jwtSubject, setJwtSubject] = useState<string | null>(null)
  const [useBackendSigner, setUseBackendSigner] = useState(true)  // Recommended by default
  const [signedPayload, setSignedPayload] = useState<any>(null)  // Backend-signed payload + headers
  const [formData, setFormData] = useState({
    provider_event_id: '',
    iban: 'AE123456789012345678901',
    user_id: '',
    amount: '',
    currency: 'AED',
    occurred_at: new Date().toISOString(),
  })

  const webhookSecret = process.env.NEXT_PUBLIC_ZAND_WEBHOOK_SECRET || ''

  // Load JWT subject on mount and watch for changes
  useEffect(() => {
    const loadSubject = () => {
      const sub = getJWTSubject()
      setJwtSubject(sub)
      if (sub) {
        setFormData(prev => ({ ...prev, user_id: sub }))
      }
    }
    
    loadSubject()
    
    // Watch for storage changes (e.g., when token is updated in TokenBar)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'dev_jwt_token') {
        loadSubject()
      }
    }
    window.addEventListener('storage', handleStorageChange)
    
    // Also check periodically in case of same-window updates (sessionStorage doesn't trigger storage event)
    const interval = setInterval(loadSubject, 1000)
    
    return () => {
      window.removeEventListener('storage', handleStorageChange)
      clearInterval(interval)
    }
  }, [])

  const generateHMAC = async (payload: string): Promise<string> => {
    if (!webhookSecret) {
      throw new Error('NEXT_PUBLIC_ZAND_WEBHOOK_SECRET not set')
    }
    // Use Web Crypto API for HMAC in browser (dev-only, legacy)
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

  // Call backend signer endpoint (DEV-ONLY, recommended)
  const signWithBackend = async () => {
    if (!jwtSubject) {
      throw new Error('JWT required (missing sub)')
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/dev/v1/webhooks/zand/deposit/sign`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider_event_id: formData.provider_event_id || globalThis.crypto.randomUUID(),
          iban: formData.iban,
          user_sub: jwtSubject,
          amount: formData.amount || '1000.00',
          currency: formData.currency,
          occurred_at: formData.occurred_at,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        const traceId = response.headers.get('X-Trace-ID')
        throw {
          code: errorData.error?.code || `HTTP_${response.status}`,
          message: errorData.error?.message || response.statusText,
          details: errorData.error?.details,
          trace_id: traceId || errorData.error?.trace_id,
        } as ApiError
      }

      const data = await response.json()
      setSignedPayload(data)
      return data
    } catch (err: any) {
      if (err.code) {
        // Already formatted as ApiError
        throw err
      }
      // Network error
      throw {
        code: 'NETWORK_ERROR',
        message: err.message || 'Failed to call backend signer',
        details: { originalError: err.message },
      } as ApiError
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Ensure we have a valid user_id from JWT
    if (!jwtSubject) {
      setError({
        code: 'JWT_REQUIRED',
        message: 'JWT required (missing sub). Paste a valid token above.',
      })
      return
    }
    
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      let signature: string
      let timestamp: string
      let payloadToSend: any

      if (useBackendSigner) {
        // Use backend signer (recommended - eliminates signature mismatches)
        const signed = await signWithBackend()
        signature = signed.headers['X-Zand-Signature']
        timestamp = signed.headers['X-Zand-Timestamp']
        payloadToSend = signed.payload
      } else {
        // Legacy client-side signature (dev-only)
        payloadToSend = {
          ...formData,
          user_id: jwtSubject,
        }
        const payloadStr = JSON.stringify(payloadToSend)
        signature = await generateHMAC(payloadStr)
        timestamp = Math.floor(Date.now() / 1000).toString()
      }

      const data = await webhooksApi.zandDeposit(payloadToSend, signature, timestamp)
      setResponse(data)
      // Generate new provider_event_id for next request
      setFormData(prev => ({ ...prev, provider_event_id: globalThis.crypto.randomUUID() }))
      setSignedPayload(null)  // Clear signed payload after successful send
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
      <h1 className="text-3xl font-bold mb-6">ZAND Webhook Simulator</h1>

      {!useBackendSigner && !webhookSecret && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-6">
          <div className="text-yellow-800 font-semibold">Warning</div>
          <div className="text-yellow-600 text-sm mt-1">
            NEXT_PUBLIC_ZAND_WEBHOOK_SECRET is not set. Webhook signature will fail (client-side mode).
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={useBackendSigner}
                onChange={(e) => setUseBackendSigner(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm font-medium text-gray-700">
                Use backend signer (recommended)
              </span>
            </label>
            <p className="text-xs text-gray-500 mt-1 ml-6">
              {useBackendSigner
                ? 'Backend generates exact signed payload (eliminates signature mismatches)'
                : 'Legacy client-side signature (dev-only)'}
            </p>
          </div>
        </div>

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
              User (sub) *
            </label>
            <input
              type="text"
              value={jwtSubject || ''}
              readOnly
              placeholder="Auto-filled from JWT (sub)"
              className={`w-full px-3 py-2 border rounded-md font-mono text-sm ${
                jwtSubject
                  ? 'border-gray-300 bg-gray-50 text-gray-700'
                  : 'border-red-300 bg-red-50 text-red-700'
              }`}
            />
            {!jwtSubject && (
              <p className="mt-1 text-sm text-red-600">
                JWT required (missing sub). Paste a valid token above.
              </p>
            )}
            <p className="mt-1 text-xs text-gray-500">
              Auto-filled from JWT (sub). In production, ZAND webhooks are correlated via IBAN mapping.
            </p>
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
            disabled={loading || (!useBackendSigner && !webhookSecret) || !jwtSubject}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Sending...' : 'Send Webhook'}
          </button>
        </form>

        {useBackendSigner && signedPayload && (
          <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-md">
            <div className="text-sm font-medium text-gray-700 mb-2">Backend-Signed Payload & Headers:</div>
            <div className="text-xs font-mono bg-white p-3 rounded border overflow-x-auto">
              <div className="mb-2">
                <span className="font-semibold">Headers:</span>
                <pre className="mt-1">{JSON.stringify(signedPayload.headers, null, 2)}</pre>
              </div>
              <div>
                <span className="font-semibold">Payload:</span>
                <pre className="mt-1">{JSON.stringify(signedPayload.payload, null, 2)}</pre>
              </div>
            </div>
          </div>
        )}
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
          <div className="text-green-600 text-sm mt-2 space-y-1">
            <div>Status: <span className="font-semibold">{response.status || 'accepted'}</span></div>
            <div>Transaction ID: <span className="font-mono">{response.transaction_id}</span></div>
            {response.trace_id && (
              <div>Trace ID: <span className="font-mono">{response.trace_id}</span></div>
            )}
          </div>
          <div className="mt-3 pt-3 border-t border-green-200">
            <div className="text-xs text-green-700 font-medium mb-1">Full Response:</div>
            <pre className="text-xs bg-green-100 p-2 rounded overflow-x-auto font-mono">
              {JSON.stringify(response, null, 2)}
            </pre>
          </div>
        </div>
      )}
      
      {error && error.trace_id && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mt-2">
          <div className="text-yellow-800 text-xs">
            <span className="font-semibold">Trace ID:</span>{' '}
            <span className="font-mono">{error.trace_id}</span>
            {' '}(Use this to debug in backend logs)
          </div>
        </div>
      )}
    </div>
  )
}
