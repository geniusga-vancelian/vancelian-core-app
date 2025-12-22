"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { offersAdminApi, parseApiError, type Offer } from "@/lib/api"

export default function OffersPage() {
  const router = useRouter()
  const [offers, setOffers] = useState<Offer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)

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
      if (apiError.code) {
        setError(`${apiError.code}: ${apiError.message}`)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleStatusAction = async (e: React.MouseEvent, offerId: string, action: 'publish' | 'pause' | 'close') => {
    e.stopPropagation()
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

  const formatDateTime = (dateString: string | undefined): string => {
    if (!dateString) return "-"
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

  if (loading && offers.length === 0) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Offers</h1>
        <p className="text-gray-500">Loading...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8 max-w-7xl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Offers</h1>
        <Link
          href="/offers/new"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          Create Offer
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800 font-medium">{error}</div>
          {traceId && (
            <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
          )}
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
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All</option>
              <option value="AED">AED</option>
            </select>
          </div>
        </div>
      </div>

      {/* Offers Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Currency</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Max Amount</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Invested</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Remaining</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Maturity Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Updated At</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {offers.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                    No offers found
                  </td>
                </tr>
              ) : (
                offers.map((offer) => (
                  <tr
                    key={offer.id}
                    onClick={() => router.push(`/offers/${offer.id}`)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{offer.name}</div>
                      <div className="text-xs text-gray-500 font-mono">{offer.code}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{offer.currency}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-mono text-gray-900">
                      {parseFloat(offer.max_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-mono text-gray-700">
                      {parseFloat(offer.committed_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-mono text-green-600">
                      {parseFloat(offer.remaining_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(offer.status)}`}>
                        {offer.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDateTime(offer.maturity_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDateTime(offer.updated_at)}
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
