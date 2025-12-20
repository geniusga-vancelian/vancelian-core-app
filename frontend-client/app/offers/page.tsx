"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { getToken, offersApi, type Offer } from "@/lib/api"
import { OfferImageCarousel } from "@/components/offers/OfferImageCarousel"

export default function OffersPage() {
  const router = useRouter()
  const [offers, setOffers] = useState<Offer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const checkAuth = () => {
      const authToken = getToken()
      if (!authToken) {
        router.push("/login")
        return
      }
      loadOffers()
    }
    checkAuth()
  }, [router])

  const loadOffers = async () => {
    setLoading(true)
    setError(null)

    try {
      // Only show LIVE offers
      const data = await offersApi.listOffers({ status: 'LIVE', limit: 50 })
      setOffers(data)
    } catch (err: any) {
      setError(err.message || "Failed to load offers")
      if (err.status === 401 || err.status === 403) {
        setTimeout(() => router.push('/login'), 2000)
      }
    } finally {
      setLoading(false)
    }
  }

  const getImages = (offer: Offer): Array<{ id: string; url: string | null; is_cover: boolean }> => {
    if (!offer.media || offer.media.length === 0) return []
    
    // Filter only images (include those without URL - will fetch presigned URL)
    const images = offer.media
      .filter(m => m.type === 'IMAGE')
      .map(m => ({ id: m.id, url: m.url || null, is_cover: m.is_cover || false }))
    
    // Sort: cover image first, then by sort_order if available
    return images.sort((a, b) => {
      if (a.is_cover) return -1
      if (b.is_cover) return 1
      return 0
    })
  }

  const getProgressPercentage = (offer: Offer): number => {
    const committed = parseFloat(offer.committed_amount)
    const max = parseFloat(offer.max_amount)
    if (max === 0) return 0
    return Math.min((committed / max) * 100, 100)
  }

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Investment Offers</h1>
        <p className="text-gray-500">Loading...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8">
      <div className="mb-6">
        <Link href="/" className="text-blue-600 hover:underline inline-flex items-center gap-2">
          ← Back to Dashboard
        </Link>
      </div>

      <h1 className="text-3xl font-bold mb-6">Investment Offers</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {offers.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">No offers available at the moment</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {offers.map((offer) => {
            const images = getImages(offer)
            const progress = getProgressPercentage(offer)
            const remaining = parseFloat(offer.remaining_amount)
            const isFull = remaining <= 0

            return (
              <Link
                key={offer.id}
                href={`/offers/${offer.id}`}
                className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
              >
                {/* Image Section - Carousel if multiple, single if one */}
                <OfferImageCarousel images={images} offerName={offer.name} offerId={offer.id} />

                <div className="p-6">
                  {/* Header */}
                  <div className="mb-3">
                    <h2 className="text-xl font-bold text-gray-900 mb-1">{offer.name}</h2>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                        {offer.status}
                      </span>
                      <span className="text-xs text-gray-500 font-mono">{offer.code}</span>
                    </div>
                  </div>

                  {/* Progress */}
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-gray-600 mb-1">
                      <span>Funded</span>
                      <span className="font-semibold">{progress.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>
                        {parseFloat(offer.committed_amount).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} {offer.currency}
                      </span>
                      <span>
                        {parseFloat(offer.max_amount).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} {offer.currency}
                      </span>
                    </div>
                  </div>

                  {/* Details */}
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Remaining:</span>
                      <span className={`font-semibold font-mono ${
                        isFull ? 'text-red-600' : 'text-green-600'
                      }`}>
                        {remaining.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                      </span>
                    </div>
                    {offer.maturity_date && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Maturity:</span>
                        <span className="font-semibold">
                          {new Date(offer.maturity_date).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* CTA */}
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="text-center">
                      <span className="text-blue-600 font-semibold text-sm">
                        {isFull ? 'Full' : 'View Details →'}
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </main>
  )
}

