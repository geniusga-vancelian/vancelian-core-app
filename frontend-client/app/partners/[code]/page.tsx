"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { partnersApi, parseApiError, type PartnerDetail } from "@/lib/api"
import { MarkdownProse } from "@/components/MarkdownProse"

export default function PartnerDetailPage() {
  const params = useParams()
  const router = useRouter()
  const codeOrId = params.code as string

  const [partner, setPartner] = useState<PartnerDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (codeOrId) {
      loadPartner()
    }
  }, [codeOrId])

  const loadPartner = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await partnersApi.getPartner(codeOrId)
      setPartner(data)
    } catch (err: any) {
      const apiError = err.status ? await parseApiError(err) : { message: err.message || 'Failed to load partner' }
      setError(apiError.message || 'Failed to load partner')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string | null | undefined): string => {
    if (!dateString) return ""
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return ""
    }
  }

  if (loading) {
    return (
      <main className="container mx-auto px-4 py-8 max-w-7xl">
        <p className="text-gray-500">Loading partner...</p>
      </main>
    )
  }

  if (error || !partner) {
    return (
      <main className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error || "Partner not found"}</div>
        </div>
      </main>
    )
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-10">
      {/* Back link */}
      <div className="mb-6">
        <Link href="/partners" className="text-blue-600 hover:underline text-sm">
          ← Back to Partners
        </Link>
      </div>

      {/* Hero Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 mb-8">
        <div className="flex flex-col md:flex-row gap-6">
          {/* Logo/CEO Photo */}
          {partner.ceo_photo_url && (
            <div className="flex-shrink-0">
              <img
                src={partner.ceo_photo_url}
                alt={partner.ceo_name || partner.trade_name || partner.legal_name}
                className="w-32 h-32 rounded-full object-cover border-4 border-gray-200"
              />
            </div>
          )}

          {/* Title & Info */}
          <div className="flex-1">
            <h1 className="text-4xl font-bold mb-2">{partner.trade_name || partner.legal_name}</h1>
            {partner.city && partner.country && (
              <p className="text-gray-600 mb-4">📍 {partner.city}, {partner.country}</p>
            )}
            {partner.website_url && (
              <a
                href={partner.website_url}
                target="_blank"
                rel="noreferrer"
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                Visit website →
              </a>
            )}
          </div>
        </div>

        {/* CEO Module */}
        {partner.ceo_name && (
          <div className="mt-8 pt-8 border-t border-gray-200">
            <div className="flex flex-col md:flex-row gap-6">
              {partner.ceo_photo_url && (
                <div className="flex-shrink-0">
                  <img
                    src={partner.ceo_photo_url}
                    alt={partner.ceo_name}
                    className="w-24 h-24 rounded-full object-cover"
                  />
                </div>
              )}
              <div className="flex-1">
                {partner.ceo_name && (
                  <h3 className="text-xl font-semibold mb-1">{partner.ceo_name}</h3>
                )}
                {partner.ceo_title && (
                  <p className="text-gray-600 mb-3">{partner.ceo_title}</p>
                )}
                {partner.ceo_quote && (
                  <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-700 mb-4">
                    "{partner.ceo_quote}"
                  </blockquote>
                )}
                {partner.ceo_bio_markdown && (
                  <div className="prose prose-sm max-w-none">
                    <MarkdownProse content={partner.ceo_bio_markdown} />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* About Section */}
      {partner.description_markdown && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-4">About</h2>
          <div className="prose prose-lg max-w-none">
            <MarkdownProse content={partner.description_markdown} />
          </div>
        </div>
      )}

      {/* Portfolio Projects */}
      {partner.portfolio_projects.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-6">Portfolio</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {partner.portfolio_projects.map((project) => (
              <div key={project.id} className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow">
                {project.cover_url && (
                  <img
                    src={project.cover_url}
                    alt={project.title}
                    className="w-full h-48 object-cover"
                  />
                )}
                <div className="p-4">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-semibold text-lg">{project.title}</h3>
                    {project.category && (
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                        {project.category}
                      </span>
                    )}
                  </div>
                  {project.location && (
                    <p className="text-sm text-gray-600 mb-2">📍 {project.location}</p>
                  )}
                  {project.short_summary && (
                    <p className="text-sm text-gray-700 mb-3">{project.short_summary}</p>
                  )}
                  {project.results_kpis && project.results_kpis.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {project.results_kpis.map((kpi, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded"
                        >
                          {kpi}
                        </span>
                      ))}
                    </div>
                  )}
                  {project.description_markdown && (
                    <div className="prose prose-sm max-w-none">
                      <MarkdownProse content={project.description_markdown} />
                    </div>
                  )}
                  {project.promo_video_url && (
                    <div className="mt-4">
                      <video controls className="w-full rounded-lg">
                        <source src={project.promo_video_url} type="video/mp4" />
                        Your browser does not support the video tag.
                      </video>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Media Gallery */}
      {partner.gallery.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-6">Gallery</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {partner.gallery.map((media) => (
              <div key={media.id}>
                {media.type === 'IMAGE' && media.url && (
                  <img
                    src={media.url}
                    alt=""
                    className="w-full h-48 object-cover rounded-lg"
                  />
                )}
                {media.type === 'VIDEO' && media.url && (
                  <video controls className="w-full h-48 object-cover rounded-lg">
                    <source src={media.url} type={media.mime_type} />
                  </video>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Promo Video */}
      {partner.promo_video && partner.promo_video.url && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-4">Video</h2>
          <div className="max-w-4xl">
            <video controls className="w-full rounded-lg">
              <source src={partner.promo_video.url} type={partner.promo_video.mime_type} />
              Your browser does not support the video tag.
            </video>
          </div>
        </div>
      )}

      {/* Documents */}
      {partner.documents.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-6">Documents</h2>
          <div className="space-y-3">
            {partner.documents.map((doc) => (
              <div
                key={doc.id}
                className="flex justify-between items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <div>
                  <strong className="text-gray-900">{doc.title}</strong>
                  <span className="ml-2 text-sm text-gray-500">({doc.type})</span>
                  <span className="ml-2 text-sm text-gray-500">
                    ({(doc.size_bytes / 1024 / 1024).toFixed(2)} MB)
                  </span>
                </div>
                {doc.url && (
                  <a
                    href={doc.url}
                    target="_blank"
                    rel="noreferrer"
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium"
                  >
                    Download
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related Offers */}
      {partner.related_offers.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-6">Related Offers</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {partner.related_offers.map((offer) => (
              <Link
                key={offer.id}
                href={`/offers/${offer.id}`}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{offer.name}</h3>
                  {offer.is_primary && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      Primary
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600">{offer.code}</p>
                <div className="mt-2 text-blue-600 hover:text-blue-800 text-sm font-medium">
                  View offer →
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Contact Info */}
      {(partner.contact_email || partner.contact_phone || partner.address_line1) && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
          <h2 className="text-2xl font-semibold mb-4">Contact</h2>
          <div className="space-y-2 text-gray-700">
            {partner.contact_email && (
              <p>
                <strong>Email:</strong>{" "}
                <a href={`mailto:${partner.contact_email}`} className="text-blue-600 hover:underline">
                  {partner.contact_email}
                </a>
              </p>
            )}
            {partner.contact_phone && (
              <p>
                <strong>Phone:</strong> {partner.contact_phone}
              </p>
            )}
            {partner.address_line1 && (
              <p>
                <strong>Address:</strong> {partner.address_line1}
                {partner.address_line2 && `, ${partner.address_line2}`}
                {partner.city && `, ${partner.city}`}
                {partner.country && `, ${partner.country}`}
              </p>
            )}
          </div>
        </div>
      )}
    </main>
  )
}

