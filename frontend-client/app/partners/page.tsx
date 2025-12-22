"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { partnersApi, parseApiError, type PartnerListItem } from "@/lib/api"

export default function PartnersPage() {
  const [partners, setPartners] = useState<PartnerListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadPartners()
  }, [])

  const loadPartners = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await partnersApi.listPartners({ limit: 100 })
      setPartners(data)
    } catch (err: any) {
      const apiError = err.status ? await parseApiError(err) : { message: err.message || 'Failed to load partners' }
      setError(apiError.message || 'Failed to load partners')
    } finally {
      setLoading(false)
    }
  }

  if (loading && partners.length === 0) {
    return (
      <main className="container mx-auto px-4 py-8 max-w-7xl">
        <h1 className="text-4xl font-bold mb-8">Trusted Partners</h1>
        <p className="text-gray-500">Loading partners...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto px-4 py-8 max-w-7xl">
      <h1 className="text-4xl font-bold mb-8">Trusted Partners</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      {partners.length === 0 && !loading ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-500">No partners available at the moment.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {partners.map((partner) => (
            <Link
              key={partner.id}
              href={`/partners/${partner.code}`}
              className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
            >
              {(partner.cover_image_url || partner.ceo_photo_url) ? (
                <img
                  src={partner.cover_image_url || partner.ceo_photo_url}
                  alt={partner.trade_name || partner.legal_name}
                  className="w-full h-48 object-cover"
                />
              ) : (
                <div className="w-full h-48 bg-gray-100 flex items-center justify-center">
                  <span className="text-gray-400 text-sm">No image</span>
                </div>
              )}
              <div className="p-6">
                <h3 className="text-xl font-semibold mb-2">{partner.trade_name || partner.legal_name}</h3>
                {partner.description_markdown && (
                  <p className="text-gray-600 text-sm mb-3 line-clamp-3">
                    {partner.description_markdown.replace(/[#*\[\]()]/g, '').substring(0, 150)}...
                  </p>
                )}
                {partner.city && partner.country && (
                  <p className="text-gray-500 text-xs mb-3">📍 {partner.city}, {partner.country}</p>
                )}
                {partner.website_url && (
                  <p className="text-blue-600 text-sm hover:underline">
                    Visit website →
                  </p>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  )
}

