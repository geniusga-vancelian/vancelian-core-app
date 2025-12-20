"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { getApiUrl } from "@/lib/config"
import { getToken } from "@/lib/api"
import type { Offer, DocumentItem } from "@/lib/api"

interface OfferContentSectionsProps {
  offer: Offer
  relatedOffers?: Offer[]
}

export function OfferContentSections({ offer, relatedOffers = [] }: OfferContentSectionsProps) {
  const [showFullDescription, setShowFullDescription] = useState(false)
  const [documentUrls, setDocumentUrls] = useState<Record<string, string>>({})
  const [downloadingDocs, setDownloadingDocs] = useState<Record<string, boolean>>({})

  // Fetch presigned URLs for documents without URLs
  useEffect(() => {
    const fetchPresignedUrls = async () => {
      if (!offer.documents || offer.documents.length === 0) return
      
      const urls: Record<string, string> = {}
      
      // Fetch presigned URLs for documents without URLs
      for (const doc of offer.documents) {
        if (!doc.url && doc.id) {
          try {
            const token = getToken()
            const response = await fetch(
              getApiUrl(`api/v1/offers/${offer.id}/documents/${doc.id}/download`),
              {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
              }
            )
            if (response.ok) {
              const data = await response.json()
              if (data.download_url) {
                urls[doc.id] = data.download_url
              }
            }
          } catch (err) {
            console.warn(`Failed to fetch presigned URL for document ${doc.id}:`, err)
          }
        } else if (doc.url) {
          urls[doc.id] = doc.url
        }
      }
      
      setDocumentUrls(urls)
    }
    
    fetchPresignedUrls()
  }, [offer.documents, offer.id])

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Use Marketing V1.1 fields from API (not metadata)
  const marketingWhy = offer.marketing_why || []
  const marketingHighlights = offer.marketing_highlights || []
  const breakdown = offer.marketing_breakdown || {
    purchase_cost: null,
    transaction_cost: null,
    running_cost: null,
  }
  const metrics = offer.marketing_metrics || {}

  return (
    <div className="space-y-8">
      {/* Why Invest */}
      <section>
        <h2 className="text-2xl font-bold mb-4">
          {offer.marketing_title || "Why invest in this property?"}
        </h2>
        {offer.marketing_subtitle && (
          <p className="text-gray-600 mb-4">{offer.marketing_subtitle}</p>
        )}
        {marketingWhy.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {marketingWhy.map((item: { title: string; body: string }, idx: number) => (
              <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-gray-700 text-sm">{item.body}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
            <p className="text-gray-500 text-center">Why invest information coming soon</p>
          </div>
        )}
      </section>

      {/* Investment Breakdown */}
      <section>
        <h2 className="text-2xl font-bold mb-4">Investment Breakdown</h2>
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full">
            <tbody className="divide-y divide-gray-200">
              <tr>
                <td className="px-6 py-4 text-sm text-gray-600">Property price</td>
                <td className="px-6 py-4 text-sm font-semibold text-right">
                  {parseFloat(offer.max_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                </td>
              </tr>
              {breakdown.purchase_cost !== null && breakdown.purchase_cost !== undefined ? (
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-600">Purchase cost</td>
                  <td className="px-6 py-4 text-sm font-semibold text-right">
                    {typeof breakdown.purchase_cost === 'number' 
                      ? breakdown.purchase_cost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                      : parseFloat(String(breakdown.purchase_cost)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    } {offer.currency}
                  </td>
                </tr>
              ) : (
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-500">Purchase cost</td>
                  <td className="px-6 py-4 text-sm text-gray-400 text-right">Not provided yet</td>
                </tr>
              )}
              {breakdown.transaction_cost !== null && breakdown.transaction_cost !== undefined ? (
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-600">Transaction cost</td>
                  <td className="px-6 py-4 text-sm font-semibold text-right">
                    {typeof breakdown.transaction_cost === 'number'
                      ? breakdown.transaction_cost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                      : parseFloat(String(breakdown.transaction_cost)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    } {offer.currency}
                  </td>
                </tr>
              ) : (
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-500">Transaction cost</td>
                  <td className="px-6 py-4 text-sm text-gray-400 text-right">Not provided yet</td>
                </tr>
              )}
              {breakdown.running_cost !== null && breakdown.running_cost !== undefined ? (
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-600">Running cost</td>
                  <td className="px-6 py-4 text-sm font-semibold text-right">
                    {typeof breakdown.running_cost === 'number'
                      ? breakdown.running_cost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                      : parseFloat(String(breakdown.running_cost)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    } {offer.currency}
                  </td>
                </tr>
              ) : (
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-500">Running cost</td>
                  <td className="px-6 py-4 text-sm text-gray-400 text-right">Not provided yet</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Description */}
      {offer.description && (
        <section>
          <h2 className="text-2xl font-bold mb-4">Description</h2>
          <div className="prose max-w-none">
            {showFullDescription ? (
              <div>
                <p className="text-gray-700 whitespace-pre-line mb-4">{offer.description}</p>
                <button
                  onClick={() => setShowFullDescription(false)}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  Show less
                </button>
              </div>
            ) : (
              <div>
                <p className="text-gray-700 line-clamp-3 mb-4">{offer.description}</p>
                {offer.description.length > 200 && (
                  <button
                    onClick={() => setShowFullDescription(true)}
                    className="text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Show more
                  </button>
                )}
              </div>
            )}
          </div>
        </section>
      )}

      {/* Highlights */}
      <section>
        <h2 className="text-2xl font-bold mb-4">Highlights</h2>
        {marketingHighlights.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {marketingHighlights.map((highlight: string, idx: number) => (
              <span
                key={idx}
                className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium"
              >
                {highlight}
              </span>
            ))}
          </div>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
            <p className="text-gray-500 text-center">Highlights coming soon</p>
          </div>
        )}
      </section>

      {/* Location */}
      <section>
        <h2 className="text-2xl font-bold mb-4">Location</h2>
        {offer.location_label ? (
          <div className="space-y-4">
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <p className="text-gray-900 font-medium">{offer.location_label}</p>
            </div>
            {offer.location_lat && offer.location_lng ? (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 h-64 flex items-center justify-center">
                <div className="text-center">
                  <div className="text-3xl mb-2">📍</div>
                  <p className="text-gray-500 text-sm mb-2">Coordinates: {parseFloat(offer.location_lat).toFixed(6)}, {parseFloat(offer.location_lng).toFixed(6)}</p>
                  <p className="text-gray-400 text-xs">Map embed coming soon</p>
                  {/* TODO: Add Google Maps embed when ready */}
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 h-64 flex items-center justify-center">
            <div className="text-center">
              <div className="text-3xl mb-2">📍</div>
              <p className="text-gray-500">Location information coming soon</p>
            </div>
          </div>
        )}
      </section>

      {/* Documents */}
      {offer.documents && offer.documents.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold mb-4">Documents</h2>
          <div className="space-y-2">
            {offer.documents.map((doc: DocumentItem) => {
              const docUrl = documentUrls[doc.id] || doc.url
              const isDownloading = downloadingDocs[doc.id] || false
              
              const handleDownload = async () => {
                if (!docUrl) {
                  // Try to fetch presigned URL on demand
                  setDownloadingDocs(prev => ({ ...prev, [doc.id]: true }))
                  try {
                    const token = getToken()
                    const response = await fetch(
                      getApiUrl(`api/v1/offers/${offer.id}/documents/${doc.id}/download`),
                      {
                        headers: token ? { Authorization: `Bearer ${token}` } : {},
                      }
                    )
                    if (response.ok) {
                      const data = await response.json()
                      if (data.download_url) {
                        // Update state and trigger download
                        setDocumentUrls(prev => ({ ...prev, [doc.id]: data.download_url }))
                        window.open(data.download_url, '_blank', 'noopener,noreferrer')
                      }
                    }
                  } catch (err) {
                    console.error(`Failed to download document ${doc.id}:`, err)
                    alert('Failed to download document. Please try again.')
                  } finally {
                    setDownloadingDocs(prev => ({ ...prev, [doc.id]: false }))
                  }
                } else {
                  // Direct download
                  window.open(docUrl, '_blank', 'noopener,noreferrer')
                }
              }
              
              return (
                <div
                  key={doc.id}
                  className="bg-white border border-gray-200 rounded-lg p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <span className="text-blue-600 font-semibold">📄</span>
                    </div>
                    <div>
                      <div className="font-medium text-gray-900">{doc.name}</div>
                      <div className="text-sm text-gray-500">
                        {doc.kind} • {formatFileSize(doc.size_bytes)}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={handleDownload}
                    disabled={isDownloading}
                    className="text-blue-600 hover:text-blue-800 font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isDownloading ? 'Loading...' : 'Download'}
                  </button>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Related Offers */}
      {relatedOffers.length > 0 && (
        <section>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">Properties for you</h2>
            <Link href="/offers" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              View All
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {relatedOffers.slice(0, 6).map((relatedOffer) => {
              const relatedProgress = parseFloat(relatedOffer.max_amount) > 0
                ? (parseFloat(relatedOffer.committed_amount) / parseFloat(relatedOffer.max_amount)) * 100
                : 0
              const relatedCover = relatedOffer.media?.find(m => m.type === 'IMAGE' && m.is_cover) || relatedOffer.media?.find(m => m.type === 'IMAGE')

              return (
                <Link
                  key={relatedOffer.id}
                  href={`/offers/${relatedOffer.id}`}
                  className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
                >
                  {relatedCover?.url ? (
                    <img
                      src={relatedCover.url}
                      alt={relatedOffer.name}
                      className="w-full h-48 object-cover"
                    />
                  ) : (
                    <div className="w-full h-48 bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                      <span className="text-gray-400 text-sm">No image</span>
                    </div>
                  )}
                  <div className="p-4">
                    <h3 className="font-semibold text-gray-900 mb-2 line-clamp-1">{relatedOffer.name}</h3>
                    <div className="flex justify-between text-sm text-gray-600 mb-2">
                      <span>{relatedOffer.currency}</span>
                      <span className="font-semibold">{relatedProgress.toFixed(0)}% funded</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${relatedProgress}%` }}
                      />
                    </div>
                  </div>
                </Link>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}

