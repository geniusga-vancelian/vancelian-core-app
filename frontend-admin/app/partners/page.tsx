"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { partnersAdminApi, parseApiError, type PartnerListItem } from "@/lib/api"

export default function PartnersPage() {
  const router = useRouter()
  const [partners, setPartners] = useState<PartnerListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [searchQuery, setSearchQuery] = useState<string>("")

  useEffect(() => {
    loadPartners()
  }, [statusFilter, searchQuery])

  const loadPartners = async () => {
    setLoading(true)
    setError(null)
    setTraceId(null)
    
    try {
      const params: any = {}
      if (statusFilter) params.status = statusFilter
      if (searchQuery) params.q = searchQuery
      
      const data = await partnersAdminApi.listPartners(params)
      setPartners(data)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to load partners")
      setTraceId(apiError.trace_id || null)
      if (apiError.code) {
        setError(`${apiError.code}: ${apiError.message}`)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleStatusAction = async (e: React.MouseEvent, partnerId: string, action: 'publish' | 'archive') => {
    e.stopPropagation()
    try {
      if (action === 'publish') {
        await partnersAdminApi.publishPartner(partnerId)
      } else if (action === 'archive') {
        await partnersAdminApi.archivePartner(partnerId)
      }
      loadPartners()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || `Failed to ${action} partner`)
      setTraceId(apiError.trace_id || null)
    }
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      DRAFT: "bg-gray-100 text-gray-800",
      PUBLISHED: "bg-green-100 text-green-800",
      ARCHIVED: "bg-red-100 text-red-800",
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

  if (loading && partners.length === 0) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Partners</h1>
        <p className="text-gray-500">Loading...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8 max-w-7xl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Partners</h1>
        <Link
          href="/partners/new"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          Create Partner
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded mb-4">
          <p>{error}</p>
          {traceId && <p className="text-sm text-red-600 mt-1">Trace ID: {traceId}</p>}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow-sm mb-6 flex gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search by name or code..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Status</option>
            <option value="DRAFT">Draft</option>
            <option value="PUBLISHED">Published</option>
            <option value="ARCHIVED">Archived</option>
          </select>
        </div>
      </div>

      {/* Partners Table */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Code</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Legal Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Trade Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Website</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Updated</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {partners.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                  No partners found
                </td>
              </tr>
            ) : (
              partners.map((partner) => (
                <tr
                  key={partner.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => router.push(`/partners/${partner.id}`)}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{partner.code}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{partner.legal_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{partner.trade_name || "-"}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadge(partner.status)}`}>
                      {partner.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {partner.website_url ? (
                      <a
                        href={partner.website_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-blue-600 hover:underline"
                      >
                        {partner.website_url}
                      </a>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDateTime(partner.updated_at)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium" onClick={(e) => e.stopPropagation()}>
                    <div className="flex gap-2">
                      {partner.status === 'DRAFT' && (
                        <button
                          onClick={(e) => handleStatusAction(e, partner.id, 'publish')}
                          className="text-green-600 hover:text-green-900"
                        >
                          Publish
                        </button>
                      )}
                      {partner.status === 'PUBLISHED' && (
                        <button
                          onClick={(e) => handleStatusAction(e, partner.id, 'archive')}
                          className="text-orange-600 hover:text-orange-900"
                        >
                          Archive
                        </button>
                      )}
                      {partner.status === 'ARCHIVED' && (
                        <button
                          onClick={(e) => handleStatusAction(e, partner.id, 'publish')}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Republish
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </main>
  )
}

