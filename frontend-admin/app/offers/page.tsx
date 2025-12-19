"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { offersAdminApi, parseApiError, type Offer, type CreateOfferPayload } from "@/lib/api"

export default function OffersPage() {
  const router = useRouter()
  const [offers, setOffers] = useState<Offer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  
  // Create form state
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createForm, setCreateForm] = useState<CreateOfferPayload>({
    code: "",
    name: "",
    description: "",
    currency: "AED",
    max_amount: "",
    maturity_date: undefined,
  })
  const [creating, setCreating] = useState(false)

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [currencyFilter, setCurrencyFilter] = useState<string>("")

  useEffect(() => {
    loadOffers()
  }, [statusFilter, currencyFilter])

  const loadOffers = async () => {
    setLoading(true)
    setError(null)
    setTraceId(null)
    
    try {
      const params: any = {}
      if (statusFilter) params.status = statusFilter as any
      if (currencyFilter) params.currency = currencyFilter
      
      const data = await offersAdminApi.listOffers(params)
      setOffers(data)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to load offers")
      setTraceId(apiError.trace_id || null)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError(null)
    setTraceId(null)

    try {
      const payload: CreateOfferPayload = {
        ...createForm,
        max_amount: createForm.max_amount,
        maturity_date: createForm.maturity_date || undefined,
      }
      const newOffer = await offersAdminApi.createOffer(payload)
      setShowCreateForm(false)
      setCreateForm({
        code: "",
        name: "",
        description: "",
        currency: "AED",
        max_amount: "",
        maturity_date: undefined,
      })
      loadOffers()
      router.push(`/offers/${newOffer.id}`)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to create offer")
      setTraceId(apiError.trace_id || null)
    } finally {
      setCreating(false)
    }
  }

  const handleStatusAction = async (offerId: string, action: 'publish' | 'pause' | 'close') => {
    try {
      if (action === 'publish') {
        await offersAdminApi.publishOffer(offerId)
      } else if (action === 'pause') {
        await offersAdminApi.pauseOffer(offerId)
      } else if (action === 'close') {
        await offersAdminApi.closeOffer(offerId)
      }
      loadOffers()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || `Failed to ${action} offer`)
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

  if (loading && offers.length === 0) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Offers</h1>
        <p>Loading...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Offers</h1>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          {showCreateForm ? "Cancel" : "Create Offer"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800">{error}</div>
          {traceId && (
            <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
          )}
        </div>
      )}

      {/* Create Form */}
      {showCreateForm && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Create New Offer</h2>
          <form onSubmit={handleCreate}>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Code *
                </label>
                <input
                  type="text"
                  required
                  value={createForm.code}
                  onChange={(e) => setCreateForm({ ...createForm, code: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="NEST-ALBARARI-001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  required
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows={3}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Currency *
                </label>
                <select
                  value={createForm.currency}
                  onChange={(e) => setCreateForm({ ...createForm, currency: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="AED">AED</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Amount *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={createForm.max_amount}
                  onChange={(e) => setCreateForm({ ...createForm, max_amount: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Maturity Date
                </label>
                <input
                  type="datetime-local"
                  value={createForm.maturity_date || ""}
                  onChange={(e) => setCreateForm({ ...createForm, maturity_date: e.target.value || undefined })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={creating}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {creating ? "Creating..." : "Create Offer"}
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All</option>
              <option value="DRAFT">DRAFT</option>
              <option value="LIVE">LIVE</option>
              <option value="PAUSED">PAUSED</option>
              <option value="CLOSED">CLOSED</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
            <select
              value={currencyFilter}
              onChange={(e) => setCurrencyFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All</option>
              <option value="AED">AED</option>
            </select>
          </div>
        </div>
      </div>

      {/* Offers Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Currency</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Max</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Committed</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Remaining</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Maturity</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {offers.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-8 text-center text-gray-500">
                    No offers found
                  </td>
                </tr>
              ) : (
                offers.map((offer) => (
                  <tr key={offer.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link href={`/offers/${offer.id}`} className="text-blue-600 hover:underline">
                        {offer.name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">{offer.code}</td>
                    <td className="px-6 py-4 whitespace-nowrap">{offer.currency}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right font-mono">
                      {parseFloat(offer.max_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right font-mono">
                      {parseFloat(offer.committed_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right font-mono">
                      {parseFloat(offer.remaining_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {offer.maturity_date ? new Date(offer.maturity_date).toLocaleDateString() : "-"}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs ${getStatusBadge(offer.status)}`}>
                        {offer.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex gap-2">
                        <Link
                          href={`/offers/${offer.id}`}
                          className="text-blue-600 hover:underline text-sm"
                        >
                          View
                        </Link>
                        {offer.status === 'DRAFT' && (
                          <button
                            onClick={() => handleStatusAction(offer.id, 'publish')}
                            className="text-green-600 hover:underline text-sm"
                          >
                            Publish
                          </button>
                        )}
                        {offer.status === 'LIVE' && (
                          <>
                            <button
                              onClick={() => handleStatusAction(offer.id, 'pause')}
                              className="text-yellow-600 hover:underline text-sm"
                            >
                              Pause
                            </button>
                            <button
                              onClick={() => handleStatusAction(offer.id, 'close')}
                              className="text-red-600 hover:underline text-sm"
                            >
                              Close
                            </button>
                          </>
                        )}
                        {offer.status === 'PAUSED' && (
                          <>
                            <button
                              onClick={() => handleStatusAction(offer.id, 'publish')}
                              className="text-green-600 hover:underline text-sm"
                            >
                              Resume
                            </button>
                            <button
                              onClick={() => handleStatusAction(offer.id, 'close')}
                              className="text-red-600 hover:underline text-sm"
                            >
                              Close
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  )
}
