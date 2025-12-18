"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { apiRequest, parseApiError, getToken } from "@/lib/api"

interface Deposit {
  transaction_id: string
  user_id: string
  email: string
  amount: string
  currency: string
  status: string
  created_at: string
  compliance_status?: string
  operation_id?: string
  operationId?: string
}

export default function CompliancePage() {
  const router = useRouter()
  const [deposits, setDeposits] = useState<Deposit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string>("")
  const [actionSuccess, setActionSuccess] = useState<string>("")
  const [selectedDeposit, setSelectedDeposit] = useState<Deposit | null>(null)
  const [showReleaseModal, setShowReleaseModal] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [reason, setReason] = useState("")

  useEffect(() => {
    const token = getToken()
    if (!token) {
      router.push("/login")
      return
    }

    fetchDeposits()
  }, [router])

  const fetchDeposits = async () => {
    try {
      setLoading(true)
      setError("")
      const data = await apiRequest<Deposit[]>('admin/v1/compliance/deposits?limit=100')
      setDeposits(data)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message)
      if (apiError.status === 401 || apiError.status === 403) {
        router.push("/login")
      }
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Compliance - Deposits</h1>
        <p>Loading deposits...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Compliance - Deposits</h1>
      
      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
          <div className="font-semibold">Error: {error}</div>
          {error.includes("COMPLIANCE") && (
            <div className="text-sm mt-1">
              This endpoint requires COMPLIANCE role. Your user may not have the required permissions.
            </div>
          )}
        </div>
      )}

      {actionError && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
          <div className="font-semibold">Action Error: {actionError}</div>
        </div>
      )}

      {actionSuccess && (
        <div className="bg-green-100 text-green-700 p-3 rounded mb-4 flex items-center justify-between">
          <div className="font-semibold">{actionSuccess}</div>
          <button
            onClick={() => setActionSuccess("")}
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
                    Transaction ID
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
                    Compliance Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {deposits.map((deposit) => (
                  <tr key={deposit.transaction_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                      {deposit.transaction_id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <Link
                        href={`/users/${deposit.user_id}`}
                        className="text-blue-600 hover:underline"
                      >
                        {deposit.email}
                      </Link>
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
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {deposit.compliance_status ? (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                          {deposit.compliance_status}
                        </span>
                      ) : (
                        <span className="text-gray-400">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {(() => {
                        const dateValue =
                          deposit.created_at ??
                          (deposit as any).createdAt ??
                          (deposit as any).occurred_at ??
                          (deposit as any).occurredAt ??
                          (deposit as any).inserted_at ??
                          (deposit as any).insertedAt ??
                          (deposit as any).updated_at ??
                          (deposit as any).updatedAt;
                        if (!dateValue) return '-';
                        try {
                          const date = new Date(dateValue);
                          if (isNaN(date.getTime())) return 'Invalid Date';
                          return date.toLocaleString('fr-FR', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          });
                        } catch {
                          return dateValue;
                        }
                      })()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {deposit.status === "COMPLIANCE_REVIEW" || deposit.compliance_status === "COMPLIANCE_REVIEW" ? (
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              setSelectedDeposit(deposit);
                              setShowReleaseModal(true);
                              setReason("");
                              setActionError("");
                              setActionSuccess("");
                            }}
                            disabled={actionLoading !== null}
                            className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-medium"
                          >
                            Release
                          </button>
                          <button
                            onClick={() => {
                              setSelectedDeposit(deposit);
                              setShowRejectModal(true);
                              setReason("");
                              setActionError("");
                              setActionSuccess("");
                            }}
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
      {showReleaseModal && selectedDeposit && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-semibold mb-4">Release Funds</h2>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!selectedDeposit || !reason) return;

                setActionLoading('release');
                setActionError("");
                setActionSuccess("");

                try {
                  const result = await apiRequest<{ transaction_id: string; status: string }>(
                    'admin/v1/compliance/release-funds',
                    {
                      method: 'POST',
                      body: JSON.stringify({
                        transaction_id: selectedDeposit.transaction_id,
                        amount: selectedDeposit.amount,
                        reason: reason || "Manual review approved (DEV)",
                      }),
                    }
                  );

                  setActionSuccess(`Funds released successfully. Status: ${result.status}`);
                  setShowReleaseModal(false);
                  setReason("");
                  setTimeout(() => {
                    fetchDeposits();
                  }, 500);
                } catch (err: any) {
                  const apiError = parseApiError(err);
                  setActionError(apiError.message || "Failed to release funds");
                  console.error('[Compliance] Release failed:', apiError);
                } finally {
                  setActionLoading(null);
                }
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Transaction ID
                </label>
                <input
                  type="text"
                  value={selectedDeposit.transaction_id}
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Amount
                </label>
                <input
                  type="text"
                  value={selectedDeposit.amount}
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason *
                </label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
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
                  onClick={() => {
                    setShowReleaseModal(false);
                    setReason("");
                  }}
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
      {showRejectModal && selectedDeposit && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-semibold mb-4">Reject Deposit</h2>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!selectedDeposit || !reason) return;

                setActionLoading('reject');
                setActionError("");
                setActionSuccess("");

                try {
                  const result = await apiRequest<{ transaction_id: string; status: string }>(
                    'admin/v1/compliance/reject-deposit',
                    {
                      method: 'POST',
                      body: JSON.stringify({
                        transaction_id: selectedDeposit.transaction_id,
                        reason: reason || "Manual review rejected (DEV)",
                      }),
                    }
                  );

                  setActionSuccess(`Deposit rejected successfully. Status: ${result.status}`);
                  setShowRejectModal(false);
                  setReason("");
                  setTimeout(() => {
                    fetchDeposits();
                  }, 500);
                } catch (err: any) {
                  const apiError = parseApiError(err);
                  setActionError(apiError.message || "Failed to reject deposit");
                  console.error('[Compliance] Reject failed:', apiError);
                } finally {
                  setActionLoading(null);
                }
              }}
              className="space-y-4"
            >
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Transaction ID
                </label>
                <input
                  type="text"
                  value={selectedDeposit.transaction_id}
                  disabled
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason *
                </label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
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
                  onClick={() => {
                    setShowRejectModal(false);
                    setReason("");
                  }}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  )
}
