"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import Link from "next/link"
import { offersAdminApi, parseApiError, type Offer, type UpdateOfferPayload } from "@/lib/api"

interface Investment {
  id: string
  offer_id: string
  user_id: string
  user_email: string
  requested_amount: string
  allocated_amount: string
  currency: string
  status: 'PENDING' | 'CONFIRMED' | 'REJECTED'
  created_at: string
  updated_at?: string
  idempotency_key?: string
}

export default function OfferDetailPage() {
  const router = useRouter()
  const params = useParams()
  const offerId = params.id as string
  
  const [offer, setOffer] = useState<Offer | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState<UpdateOfferPayload>({})
  const [saving, setSaving] = useState(false)

  // Investments state
  const [investments, setInvestments] = useState<Investment[]>([])
  const [investmentsTotal, setInvestmentsTotal] = useState(0)
  const [investmentsLoading, setInvestmentsLoading] = useState(false)
  const [investmentsError, setInvestmentsError] = useState<string | null>(null)
  const [investmentsTraceId, setInvestmentsTraceId] = useState<string | null>(null)
  const [investmentStatusFilter, setInvestmentStatusFilter] = useState<string>("ALL")

  useEffect(() => {
    if (offerId) {
      loadOffer()
      loadInvestments()
    }
  }, [offerId, investmentStatusFilter])

  const loadOffer = async () => {
    setLoading(true)
    setError(null)
    setTraceId(null)
    
    try {
      const data = await offersAdminApi.getOffer(offerId)
      setOffer(data)
      setEditForm({
        name: data.name,
        description: data.description || "",
        max_amount: data.max_amount,
        maturity_date: data.maturity_date || undefined,
      })
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || "Failed to load offer")
      setTraceId(apiError.trace_id || null)
    } finally {
      setLoading(false)
    }
  }

  const loadInvestments = async () => {
    if (!offerId) return
    
    setInvestmentsLoading(true)
    setInvestmentsError(null)
    setInvestmentsTraceId(null)
    
    try {
      const params: any = { limit: 50, offset: 0 }
      if (investmentStatusFilter && investmentStatusFilter !== "ALL") {
        params.status = investmentStatusFilter
      }
      const response = await offersAdminApi.listOfferInvestments(offerId, params)
      setInvestments(response.items || [])
      setInvestmentsTotal(response.total || 0)
    } catch (err: any) {
      console.error('[Offers Detail] Error loading investments:', err)
      const apiError = parseApiError(err)
      setInvestmentsError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || "Failed to load investments")
      setInvestmentsTraceId(apiError.trace_id || null)
    } finally {
      setInvestmentsLoading(false)
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setTraceId(null)

    try {
      const updated = await offersAdminApi.updateOffer(offerId, editForm)
      setOffer(updated)
      setEditing(false)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || "Failed to update offer")
      setTraceId(apiError.trace_id || null)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusAction = async (action: 'publish' | 'pause' | 'close') => {
    try {
      let updated: Offer
      if (action === 'publish') {
        updated = await offersAdminApi.publishOffer(offerId)
      } else if (action === 'pause') {
        updated = await offersAdminApi.pauseOffer(offerId)
      } else {
        updated = await offersAdminApi.closeOffer(offerId)
      }
      setOffer(updated)
      loadInvestments() // Refresh investments after status change
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || `Failed to ${action} offer`)
      setTraceId(apiError.trace_id || null)
    }
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      DRAFT: "bg-gray-100 text-gray-800",
      LIVE: "bg-green-100 text-green-800",
      PAUSED: "bg-yellow-100 text-yellow-800",
      CLOSED: "bg-red-100 text-red-800",
    }
    return colors[status as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  const getInvestmentStatusBadge = (status: string) => {
    const colors = {
      PENDING: "bg-yellow-100 text-yellow-800",
      CONFIRMED: "bg-green-100 text-green-800",
      REJECTED: "bg-red-100 text-red-800",
    }
    return colors[status as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  const formatDateTime = (dateString: string): string => {
    try {
      return new Date(dateString).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return "-"
    }
  }

  const getRecommendations = () => {
    if (!offer) return { warnings: [], suggestions: [], isInvestable: false }
    
    const warnings: string[] = []
    const suggestions: string[] = []
    const now = new Date()
    
    // Check maturity date
    const maturityPassed = offer.maturity_date ? new Date(offer.maturity_date) <= now : false
    const remainingAmount = parseFloat(offer.remaining_amount)
    const isLive = offer.status === 'LIVE'
    
    // Investable badge: TRUE when (status === "LIVE") AND (remaining_amount > 0) AND (maturity_date in the future)
    const isInvestable = isLive && remainingAmount > 0 && !maturityPassed
    
    // Warnings
    if (!isLive) {
      warnings.push("Offer is not LIVE (investments blocked).")
    }
    if (remainingAmount <= 0) {
      warnings.push("Offer is full (remaining = 0).")
    }
    if (maturityPassed) {
      warnings.push("Maturity date passed.")
    }
    
    // Suggested actions
    if (!isLive) {
      suggestions.push("Set to LIVE when ready to accept investments.")
    } else if (remainingAmount <= 0) {
      suggestions.push("Close offer (sold out).")
    } else if (maturityPassed) {
      suggestions.push("Close offer and prepare redemption flow.")
    } else {
      suggestions.push("Promote offer (still open).")
    }
    
    return { warnings, suggestions, isInvestable }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      // Optional: show toast notification
    })
  }

  const shortenIdempotencyKey = (key: string | undefined): string => {
    if (!key) return "-"
    return key.length > 12 ? `${key.substring(0, 8)}...` : key
  }

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <p>Loading...</p>
      </main>
    )
  }

  if (!offer) {
    return (
      <main className="container mx-auto p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Offer not found</p>
        </div>
        <Link href="/offers" className="text-blue-600 hover:underline mt-4 inline-block">
          ← Back to Offers
        </Link>
      </main>
    )
  }

  const recommendations = getRecommendations()

  return (
    <main className="container mx-auto p-8 max-w-7xl">
      <div className="mb-6">
        <Link href="/offers" className="text-blue-600 hover:underline">
          ← Back to Offers
        </Link>
      </div>

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">{offer.name}</h1>
        <div className="flex gap-2">
          {offer.status === 'DRAFT' && (
            <button
              onClick={() => handleStatusAction('publish')}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
            >
              Publish
            </button>
          )}
          {offer.status === 'LIVE' && (
            <>
              <button
                onClick={() => handleStatusAction('pause')}
                className="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700"
              >
                Pause
              </button>
              <button
                onClick={() => handleStatusAction('close')}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
              >
                Close
              </button>
            </>
          )}
          {offer.status === 'PAUSED' && (
            <>
              <button
                onClick={() => handleStatusAction('publish')}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Resume
              </button>
              <button
                onClick={() => handleStatusAction('close')}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
              >
                Close
              </button>
            </>
          )}
          <button
            onClick={() => setEditing(!editing)}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            {editing ? "Cancel Edit" : "Edit"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800">{error}</div>
          {traceId && (
            <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
          )}
        </div>
      )}

      {/* Recommendation / Ops Checklist */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recommendation / Ops Checklist</h2>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-700">Investable: </span>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              recommendations.isInvestable 
                ? "bg-green-100 text-green-800" 
                : "bg-red-100 text-red-800"
            }`}>
              {recommendations.isInvestable ? "TRUE" : "FALSE"}
            </span>
          </div>
          
          {recommendations.warnings.length > 0 && (
            <div>
              <p className="text-sm font-medium text-red-700 mb-1">Warnings:</p>
              <ul className="list-disc list-inside text-sm text-red-600 space-y-1">
                {recommendations.warnings.map((warning, idx) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
          
          {recommendations.suggestions.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-1">Suggested actions:</p>
              <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                {recommendations.suggestions.map((suggestion, idx) => (
                  <li key={idx}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Offer Details Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        {editing ? (
          <form onSubmit={handleUpdate}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input
                  type="text"
                  value={editForm.name || ""}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={editForm.description || ""}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows={4}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Amount</label>
                <input
                  type="number"
                  step="0.01"
                  value={editForm.max_amount || ""}
                  onChange={(e) => setEditForm({ ...editForm, max_amount: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Maturity Date</label>
                <input
                  type="datetime-local"
                  value={editForm.maturity_date ? new Date(editForm.maturity_date).toISOString().slice(0, 16) : ""}
                  onChange={(e) => setEditForm({ ...editForm, maturity_date: e.target.value || undefined })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditing(false)
                    setEditForm({
                      name: offer.name,
                      description: offer.description || "",
                      max_amount: offer.max_amount,
                      maturity_date: offer.maturity_date || undefined,
                    })
                  }}
                  className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Code</label>
                <p className="text-lg font-mono">{offer.code}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Status</label>
                <p>
                  <span className={`px-2 py-1 rounded text-sm ${getStatusBadge(offer.status)}`}>
                    {offer.status}
                  </span>
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Currency</label>
                <p className="text-lg">{offer.currency}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Max Amount</label>
                <p className="text-lg font-mono">
                  {parseFloat(offer.max_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Invested Amount</label>
                <p className="text-lg font-mono">
                  {parseFloat(offer.committed_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Remaining Amount</label>
                <p className="text-lg font-mono text-green-600">
                  {parseFloat(offer.remaining_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Fill Percentage</label>
                <p className="text-lg font-mono">
                  {((parseFloat(offer.committed_amount) / parseFloat(offer.max_amount)) * 100).toFixed(2)}%
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Maturity Date</label>
                <p className="text-lg">
                  {offer.maturity_date ? new Date(offer.maturity_date).toLocaleString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  }) : "-"}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Created At</label>
                <p className="text-lg">
                  {new Date(offer.created_at).toLocaleString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
              {offer.updated_at && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Updated At</label>
                  <p className="text-lg">
                    {new Date(offer.updated_at).toLocaleString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              )}
            </div>
            {offer.description && (
              <div>
                <label className="text-sm font-medium text-gray-500">Description</label>
                <p className="mt-1 text-gray-700">{offer.description}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Investments List */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Investments {investmentsTotal > 0 && `(${investmentsTotal})`}</h2>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Filter:</label>
            <select
              value={investmentStatusFilter}
              onChange={(e) => setInvestmentStatusFilter(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">ALL</option>
              <option value="PENDING">PENDING</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="REJECTED">REJECTED</option>
            </select>
          </div>
        </div>

        {investmentsError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <div className="text-red-800 font-medium">{investmentsError}</div>
            {investmentsTraceId && (
              <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {investmentsTraceId}</div>
            )}
          </div>
        )}

        {investmentsLoading ? (
          <div className="text-center py-8 text-gray-500">Loading investments...</div>
        ) : investments.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No investments found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Requested</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Allocated</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date/Time</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {investments.map((investment) => (
                  <tr key={investment.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <a 
                        href={`mailto:${investment.user_email}`}
                        className="text-blue-600 hover:underline"
                      >
                        {investment.user_email}
                      </a>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-mono text-gray-700">
                      {parseFloat(investment.requested_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-mono text-gray-700">
                      {parseFloat(investment.allocated_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getInvestmentStatusBadge(investment.status)}`}>
                        {investment.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDateTime(investment.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  )
}
