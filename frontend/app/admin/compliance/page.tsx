'use client'

import { useState, useEffect } from 'react'
import { complianceApi, ApiError } from '@/lib/api'

export default function CompliancePage() {
  const [hasAccess, setHasAccess] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [response, setResponse] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'release' | 'reject'>('release')

  // Release funds form
  const [releaseForm, setReleaseForm] = useState({
    transaction_id: '',
    amount: '',
    reason: '',
  })

  // Reject deposit form
  const [rejectForm, setRejectForm] = useState({
    transaction_id: '',
    reason: '',
  })

  useEffect(() => {
    // Check if user has admin/compliance/ops role by decoding token
    const token = sessionStorage.getItem('dev_jwt_token')
    if (token) {
      try {
        const parts = token.split('.')
        if (parts.length === 3) {
          const payload = JSON.parse(
            Buffer.from(parts[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString()
          )
          const roles = Array.isArray(payload.roles) ? payload.roles : []
          const allowedRoles = ['ADMIN', 'COMPLIANCE', 'OPS']
          setHasAccess(roles.some((r: string) => allowedRoles.includes(r.toUpperCase())))
        } else {
          setHasAccess(false)
        }
      } catch {
        setHasAccess(false)
      }
    } else {
      setHasAccess(false)
    }
  }, [])

  const handleReleaseSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const data = await complianceApi.releaseFunds(releaseForm)
      setResponse(data)
      setReleaseForm({ transaction_id: '', amount: '', reason: '' })
    } catch (err: any) {
      setError(err as ApiError)
    } finally {
      setLoading(false)
    }
  }

  const handleRejectSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResponse(null)

    try {
      const data = await complianceApi.rejectDeposit(rejectForm)
      setResponse(data)
      setRejectForm({ transaction_id: '', reason: '' })
    } catch (err: any) {
      setError(err as ApiError)
    } finally {
      setLoading(false)
    }
  }

  if (hasAccess === null) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center">Checking access...</div>
        </div>
      </div>
    )
  }

  if (!hasAccess) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg shadow p-6">
          <div className="text-red-800 font-semibold text-xl mb-2">Access Denied</div>
          <div className="text-red-600">
            This page requires ADMIN, COMPLIANCE, or OPS role.
            Please use a JWT token with one of these roles.
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Admin / Compliance</h1>

      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex">
            <button
              onClick={() => {
                setActiveTab('release')
                setError(null)
                setResponse(null)
              }}
              className={`px-4 py-3 font-medium ${
                activeTab === 'release'
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Release Funds
            </button>
            <button
              onClick={() => {
                setActiveTab('reject')
                setError(null)
                setResponse(null)
              }}
              className={`px-4 py-3 font-medium ${
                activeTab === 'reject'
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Reject Deposit
            </button>
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'release' ? (
            <form onSubmit={handleReleaseSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Transaction ID *
                </label>
                <input
                  type="text"
                  value={releaseForm.transaction_id}
                  onChange={(e) => setReleaseForm({ ...releaseForm, transaction_id: e.target.value })}
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
                  value={releaseForm.amount}
                  onChange={(e) => setReleaseForm({ ...releaseForm, amount: e.target.value })}
                  required
                  placeholder="1000.00"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reason *
                </label>
                <textarea
                  value={releaseForm.reason}
                  onChange={(e) => setReleaseForm({ ...releaseForm, reason: e.target.value })}
                  required
                  placeholder="AML review completed..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows={3}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
              >
                {loading ? 'Processing...' : 'Release Funds'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRejectSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Transaction ID *
                </label>
                <input
                  type="text"
                  value={rejectForm.transaction_id}
                  onChange={(e) => setRejectForm({ ...rejectForm, transaction_id: e.target.value })}
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
                  value={rejectForm.reason}
                  onChange={(e) => setRejectForm({ ...rejectForm, reason: e.target.value })}
                  required
                  placeholder="Sanctions match / invalid IBAN..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows={3}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400"
              >
                {loading ? 'Processing...' : 'Reject Deposit'}
              </button>
            </form>
          )}
        </div>
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
          <div className="text-green-600 text-sm mt-2">
            <div>Transaction ID: <span className="font-mono">{response.transaction_id}</span></div>
            <div className="mt-1">Status: <span className="font-semibold">{response.status}</span></div>
          </div>
        </div>
      )}
    </div>
  )
}

