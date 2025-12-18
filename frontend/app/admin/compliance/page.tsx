'use client'

import { useState, useEffect } from 'react'
import { adminApi, complianceApi, ApiError } from '@/lib/api'

interface Deposit {
  transaction_id: string
  user_id: string
  email: string
  amount: string
  currency: string
  status: string
  created_at: string
  compliance_status?: string
}

export default function CompliancePage() {
  const [deposits, setDeposits] = useState<Deposit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionError, setActionError] = useState<ApiError | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)
  
  // Modal state
  const [showReleaseModal, setShowReleaseModal] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [selectedTransaction, setSelectedTransaction] = useState<Deposit | null>(null)
  
  // Form state
  const [releaseReason, setReleaseReason] = useState('')
  const [releaseAmount, setReleaseAmount] = useState('')
  const [rejectReason, setRejectReason] = useState('')

  useEffect(() => {
    fetchDeposits()
  }, [])

  const fetchDeposits = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.listDeposits(100, 0)
      setDeposits(data)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError)
      console.error('[Compliance] Failed to fetch deposits:', {
        url: '/admin/v1/compliance/deposits',
        status: apiError.code,
        message: apiError.message,
        trace_id: apiError.trace_id,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleRelease = (deposit: Deposit) => {
    setSelectedTransaction(deposit)
    setReleaseAmount(deposit.amount)
    setReleaseReason('')
    setShowReleaseModal(true)
    setActionError(null)
    setActionSuccess(null)
  }

  const handleReject = (deposit: Deposit) => {
    setSelectedTransaction(deposit)
    setRejectReason('')
    setShowRejectModal(true)
    setActionError(null)
    setActionSuccess(null)
  }

  const submitRelease = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedTransaction || !releaseReason || !releaseAmount) return

    setActionLoading('release')
    setActionError(null)
    setActionSuccess(null)

    try {
      const result = await complianceApi.releaseFunds({
        transaction_id: selectedTransaction.transaction_id,
        amount: releaseAmount,
        reason: releaseReason,
      })
      
      setActionSuccess(`Funds released successfully. Status: ${result.status}`)
      setShowReleaseModal(false)
      setReleaseReason('')
      setReleaseAmount('')
      // Refresh deposits list after a short delay to allow backend to update
      setTimeout(() => {
        fetchDeposits()
      }, 500)
    } catch (err: any) {
      const apiError = err as ApiError
      setActionError(apiError)
      console.error('[Compliance] Release failed:', {
        url: '/admin/v1/compliance/release-funds',
        status: apiError.code,
        message: apiError.message,
        trace_id: apiError.trace_id,
      })
    } finally {
      setActionLoading(null)
    }
  }

  const submitReject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedTransaction || !rejectReason) return

    setActionLoading('reject')
    setActionError(null)
    setActionSuccess(null)

    try {
      const result = await complianceApi.rejectDeposit({
        transaction_id: selectedTransaction.transaction_id,
        reason: rejectReason,
      })
      
      setActionSuccess(`Deposit rejected successfully. Status: ${result.status}`)
      setShowRejectModal(false)
      setRejectReason('')
      // Refresh deposits list after a short delay to allow backend to update
      setTimeout(() => {
        fetchDeposits()
      }, 500)
    } catch (err: any) {
      const apiError = err as ApiError
      setActionError(apiError)
      console.error('[Compliance] Reject failed:', {
        url: '/admin/v1/compliance/reject-deposit',
        status: apiError.code,
        message: apiError.message,
        trace_id: apiError.trace_id,
      })
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Compliance - Deposits</h1>
        <p>Loading deposits...</p>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Compliance - Deposits</h1>
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          <div className="font-semibold">Error: {error.message}</div>
          {error.code && <div className="text-sm">Code: {error.code}</div>}
          {error.trace_id && (
            <div className="text-xs font-mono mt-1">Trace ID: {error.trace_id}</div>
          )}
        </div>
      )}

      {actionError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          <div className="font-semibold">Action Error: {actionError.message}</div>
          {actionError.code && <div className="text-sm">Code: {actionError.code}</div>}
          {actionError.trace_id && (
            <div className="text-xs font-mono mt-1">Trace ID: {actionError.trace_id}</div>
          )}
        </div>
      )}

      {actionSuccess && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4 flex items-center justify-between">
          <div className="font-semibold">{actionSuccess}</div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-xs text-green-600 hover:text-green-800 underline ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Deposits Pending Review ({deposits.length})</h2>
        </div>
        {deposits.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No deposits found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Transaction ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {deposits.map((deposit) => (
                  <tr key={deposit.transaction_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {(() => {
                        const dateValue = deposit.created_at || deposit.occurred_at || deposit.inserted_at
                        if (!dateValue) return '-'
                        try {
                          const date = new Date(dateValue)
                          if (isNaN(date.getTime())) return 'Invalid Date'
                          return date.toLocaleString('fr-FR', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })
                        } catch {
                          return dateValue
                        }
                      })()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {deposit.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {deposit.amount} {deposit.currency}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span
                        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          deposit.status === "AVAILABLE"
                            ? "bg-green-100 text-green-800"
                            : deposit.status === "COMPLIANCE_REVIEW"
                            ? "bg-yellow-100 text-yellow-800"
                            : deposit.status === "INITIATED"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {deposit.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-500">
                      {deposit.transaction_id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {deposit.status === "COMPLIANCE_REVIEW" ? (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleRelease(deposit)}
                            disabled={actionLoading !== null}
                            className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-medium"
                          >
                            Release
                          </button>
                          <button
                            onClick={() => handleReject(deposit)}
                            disabled={actionLoading !== null}
                            className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-medium"
                          >
                            Reject
                          </button>
                        </div>
                      ) : deposit.status === "AVAILABLE" ? (
                        <span className="text-green-600 text-xs font-semibold">Released</span>
                      ) : deposit.status === "FAILED" || deposit.status === "CANCELLED" ? (
                        <span className="text-red-600 text-xs font-semibold">Rejected</span>
                      ) : (
                        <span className="text-gray-400 text-xs">{deposit.status}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Release Modal */}
      {showReleaseModal && selectedTransaction && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-semibold mb-4">Release Funds</h2>
            <form onSubmit={submitRelease} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Transaction ID
                </label>
                <input
                  type="text"
                  value={selectedTransaction.transaction_id}
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Amount *
                </label>
                <input
                  type="text"
                  value={releaseAmount}
                  onChange={(e) => setReleaseAmount(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason *
                </label>
                <textarea
                  value={releaseReason}
                  onChange={(e) => setReleaseReason(e.target.value)}
                  required
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="AML review completed..."
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={actionLoading === 'release'}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  {actionLoading === 'release' ? 'Processing...' : 'Release Funds'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowReleaseModal(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && selectedTransaction && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-semibold mb-4">Reject Deposit</h2>
            <form onSubmit={submitReject} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Transaction ID
                </label>
                <input
                  type="text"
                  value={selectedTransaction.transaction_id}
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason *
                </label>
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  required
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="Sanctions match / invalid IBAN..."
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={actionLoading === 'reject'}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
                >
                  {actionLoading === 'reject' ? 'Processing...' : 'Reject Deposit'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowRejectModal(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
