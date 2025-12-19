"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter, useParams } from "next/navigation"
import Link from "next/link"
import { getToken, apiRequest, offersApi, type Offer, type InvestInOfferResponse, type MediaItem, type DocumentItem } from "@/lib/api"
import { formatDate } from "@/lib/format"

interface WalletBalance {
  currency: string
  total_balance: string
  available_balance: string
  blocked_balance: string
  locked_balance: string
}

export default function OfferDetailPage() {
  const router = useRouter()
  const params = useParams()
  const offerId = params.id as string

  const [offer, setOffer] = useState<Offer | null>(null)
  const [wallet, setWallet] = useState<WalletBalance | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)

  // Media carousel
  const [currentImageIndex, setCurrentImageIndex] = useState(0)
  const [showGallery, setShowGallery] = useState(false)
  const [showVideoModal, setShowVideoModal] = useState(false)

  // Investment
  const [amount, setAmount] = useState("")
  const [investing, setInvesting] = useState(false)
  const [investmentResult, setInvestmentResult] = useState<InvestInOfferResponse | null>(null)

  useEffect(() => {
    const checkAuth = () => {
      const authToken = getToken()
      if (!authToken) {
        router.push("/login")
        return
      }
      loadData()
    }
    checkAuth()
  }, [offerId, router])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    setTraceId(null)

    try {
      // Load offer details
      const offerData = await offersApi.getOffer(offerId)
      setOffer(offerData)

      // Load wallet balance
      const walletResponse = await apiRequest(`api/v1/wallet?currency=${offerData.currency}`)
      if (walletResponse.ok) {
        const walletData = await walletResponse.json()
        setWallet(walletData)
      }
    } catch (err: any) {
      setError(err.message || "Failed to load offer")
      setTraceId(err.trace_id || null)

      if (err.status === 401 || err.status === 403) {
        setTimeout(() => router.push('/login'), 2000)
      } else if (err.status === 404) {
        setError("Offer not found")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleInvest = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!amount || !offer) return

    const amountNum = parseFloat(amount)
    if (isNaN(amountNum) || amountNum <= 0) {
      setError("Invalid amount")
      return
    }

    const remaining = parseFloat(offer.remaining_amount)
    if (amountNum > remaining) {
      setError(`Maximum available: ${remaining.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${offer.currency}`)
      return
    }

    if (wallet && amountNum > parseFloat(wallet.available_balance)) {
      setError(`Insufficient balance. Available: ${parseFloat(wallet.available_balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${wallet.currency}`)
      return
    }

    setInvesting(true)
    setError(null)
    setTraceId(null)
    setInvestmentResult(null)

    try {
      const idempotencyKey = `invest-${offerId}-${Date.now()}-${Math.random().toString(36).substring(7)}`

      const result = await offersApi.invest(offerId, {
        amount: amount,
        currency: offer.currency,
        idempotency_key: idempotencyKey,
      })

      setInvestmentResult(result)
      setAmount("")

      // Reload after success
      setTimeout(() => {
        loadData()
      }, 1000)
    } catch (err: any) {
      if (err.code === 'OFFER_FULL') {
        setError("Offer is full. Please choose another offer.")
      } else if (err.code === 'INSUFFICIENT_FUNDS' || err.code === 'INSUFFICIENT_AVAILABLE_FUNDS') {
        setError("Insufficient balance for this investment.")
      } else if (err.code === 'OFFER_NOT_LIVE' || err.code === 'OFFER_CLOSED') {
        setError("This offer is no longer available.")
      } else {
        setError(err.message || "Investment failed")
      }
      
      setTraceId(err.trace_id || null)
    } finally {
      setInvesting(false)
    }
  }

  const getImages = (): MediaItem[] => {
    if (!offer?.media) return []
    return offer.media.filter(m => m.type === 'IMAGE').sort((a, b) => a.sort_order - b.sort_order)
  }

  const getPromoVideo = (): MediaItem | null => {
    if (!offer?.media) return null
    return offer.media.find(m => m.type === 'VIDEO') || null
  }

  const getCoverImage = (): MediaItem | null => {
    const images = getImages()
    return images.find(m => m.is_cover) || images[0] || null
  }

  const getProgressPercentage = (): number => {
    if (!offer) return 0
    const committed = parseFloat(offer.committed_amount)
    const max = parseFloat(offer.max_amount)
    if (max === 0) return 0
    return Math.min((committed / max) * 100, 100)
  }

  const getMaxInvestable = (): number => {
    if (!offer || !wallet) return 0
    const remaining = parseFloat(offer.remaining_amount)
    const available = parseFloat(wallet.available_balance)
    return Math.min(remaining, available)
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const quickAmounts = offer?.currency === 'AED' ? [2000, 3000, 5000, 10000] : []

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <div className="text-center py-12">
          <p className="text-gray-500">Loading...</p>
        </div>
      </main>
    )
  }

  if (!offer) {
    return (
      <main className="container mx-auto p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error || "Offer not found"}</p>
        </div>
        <Link href="/offers" className="text-blue-600 hover:underline">
          ← Back to Offers
        </Link>
      </main>
    )
  }

  const images = getImages()
  const promoVideo = getPromoVideo()
  const coverImage = getCoverImage()
  const progress = getProgressPercentage()
  const remaining = parseFloat(offer.remaining_amount)
  const isFull = remaining <= 0
  const maxInvestable = getMaxInvestable()
  const currentImage = images[currentImageIndex] || coverImage

  return (
    <main className="container mx-auto p-8 max-w-7xl">
      <div className="mb-6">
        <Link href="/offers" className="text-blue-600 hover:underline inline-flex items-center gap-2">
          ← Back to Offers
        </Link>
      </div>

      {/* Hero Carousel */}
      <div className="relative mb-8">
        {currentImage?.url ? (
          <div className="relative w-full h-96 bg-gray-200 rounded-lg overflow-hidden">
            <img
              src={currentImage.url}
              alt={offer.name}
              className="w-full h-full object-cover"
            />
            {images.length > 1 && (
              <>
                <button
                  onClick={() => setCurrentImageIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1))}
                  className="absolute left-4 top-1/2 -translate-y-1/2 bg-black/50 text-white p-2 rounded-full hover:bg-black/70"
                >
                  ←
                </button>
                <button
                  onClick={() => setCurrentImageIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0))}
                  className="absolute right-4 top-1/2 -translate-y-1/2 bg-black/50 text-white p-2 rounded-full hover:bg-black/70"
                >
                  →
                </button>
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
                  {images.map((_, idx) => (
                    <button
                      key={idx}
                      onClick={() => setCurrentImageIndex(idx)}
                      className={`w-2 h-2 rounded-full ${
                        idx === currentImageIndex ? 'bg-white' : 'bg-white/50'
                      }`}
                    />
                  ))}
                </div>
              </>
            )}
            {images.length > 1 && (
              <button
                onClick={() => setShowGallery(true)}
                className="absolute top-4 right-4 bg-white/90 text-gray-800 px-4 py-2 rounded-lg hover:bg-white font-medium text-sm"
              >
                Gallery
              </button>
            )}
          </div>
        ) : (
          <div className="w-full h-96 bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg flex items-center justify-center">
            <span className="text-gray-400">No image available</span>
          </div>
        )}

        {/* Promo Video Button */}
        {promoVideo && (
          <div className="mt-4">
            <button
              onClick={() => setShowVideoModal(true)}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 font-semibold flex items-center gap-2"
            >
              ▶ Watch Video
            </button>
          </div>
        )}
      </div>

      {/* Main Layout: Content + Sticky Invest Module */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Main Content */}
        <div className="lg:col-span-2 space-y-8">
          {/* Header */}
          <div>
            <h1 className="text-4xl font-bold mb-2">{offer.name}</h1>
            <div className="flex items-center gap-3 mb-4">
              <span className="px-3 py-1 text-sm font-semibold rounded-full bg-green-100 text-green-800">
                {offer.status}
              </span>
              <span className="text-sm text-gray-500 font-mono">{offer.code}</span>
            </div>

            {/* Progress */}
            <div className="mb-4">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Funded</span>
                <span className="font-semibold">{progress.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="flex justify-between text-sm mt-2">
                <span className="text-gray-600">
                  {parseFloat(offer.committed_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                </span>
                <span className="text-gray-600">
                  of {parseFloat(offer.max_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                </span>
              </div>
            </div>
          </div>

          {/* Why Invest */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Why Invest</h2>
            {offer.description ? (
              <div className="prose max-w-none">
                <p className="text-gray-700 mb-4">{offer.description}</p>
                {offer.metadata?.highlights && Array.isArray(offer.metadata.highlights) && (
                  <ul className="list-disc list-inside space-y-2 text-gray-700">
                    {offer.metadata.highlights.map((highlight: string, idx: number) => (
                      <li key={idx}>{highlight}</li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              <p className="text-gray-500">No description available.</p>
            )}
          </div>

          {/* Investment Breakdown (Placeholder) */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Investment Breakdown</h2>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
              <p className="text-gray-500 text-center">Details coming soon</p>
            </div>
          </div>

          {/* Amenities (Placeholder) */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Amenities</h2>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
              <p className="text-gray-500 text-center">Amenities list coming soon</p>
            </div>
          </div>

          {/* Location (Placeholder) */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Location</h2>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 h-64 flex items-center justify-center">
              <p className="text-gray-500">Map embed coming soon</p>
            </div>
          </div>

          {/* Documents */}
          {offer.documents && offer.documents.length > 0 && (
            <div>
              <h2 className="text-2xl font-bold mb-4">Documents</h2>
              <div className="space-y-2">
                {offer.documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="bg-white border border-gray-200 rounded-lg p-4 flex items-center justify-between hover:bg-gray-50"
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
                    {doc.url ? (
                      <a
                        href={doc.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                      >
                        Download
                      </a>
                    ) : (
                      <span className="text-gray-400 text-sm">No download available</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Sticky Invest Module */}
        <div className="lg:col-span-1">
          <div className="sticky top-8">
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Invest Now</h2>

              {/* Available Balance */}
              {wallet && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
                  <div className="text-sm text-gray-600 mb-1">Available Balance</div>
                  <div className="text-2xl font-bold text-green-600">
                    {parseFloat(wallet.available_balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {wallet.currency}
                  </div>
                </div>
              )}

              {/* Error Message */}
              {error && !investmentResult && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                  <div className="text-red-800 text-sm">{error}</div>
                  {traceId && (
                    <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
                  )}
                </div>
              )}

              {/* Success Message */}
              {investmentResult && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                  <h3 className="font-semibold text-green-800 mb-2">✅ Investment Successful!</h3>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-700">Requested:</span>
                      <span className="font-mono font-semibold">
                        {parseFloat(investmentResult.requested_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {investmentResult.currency}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-700">Allocated:</span>
                      <span className="font-mono font-semibold text-green-600">
                        {parseFloat(investmentResult.accepted_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {investmentResult.currency}
                      </span>
                    </div>
                    {parseFloat(investmentResult.accepted_amount) < parseFloat(investmentResult.requested_amount) && (
                      <div className="mt-2 pt-2 border-t border-green-200">
                        <p className="text-yellow-700 font-semibold text-xs">
                          ⚠️ Partial fill: Only {parseFloat(investmentResult.accepted_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {investmentResult.currency} was available
                        </p>
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => {
                      setInvestmentResult(null)
                      setAmount("")
                      loadData()
                    }}
                    className="mt-3 w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm"
                  >
                    Invest Again
                  </button>
                </div>
              )}

              {/* Investment Form */}
              {!investmentResult && (
                <>
                  {isFull ? (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                      <p className="text-red-800 font-semibold">This offer is full</p>
                    </div>
                  ) : (
                    <form onSubmit={handleInvest}>
                      {/* Quick Amount Chips */}
                      {quickAmounts.length > 0 && (
                        <div className="mb-4">
                          <div className="text-sm text-gray-600 mb-2">Quick amounts:</div>
                          <div className="flex flex-wrap gap-2">
                            {quickAmounts.map((qty) => (
                              <button
                                key={qty}
                                type="button"
                                onClick={() => setAmount(String(qty))}
                                className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium"
                              >
                                {qty.toLocaleString('en-US')} {offer.currency}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Amount ({offer.currency})
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          min="0.01"
                          max={maxInvestable}
                          value={amount}
                          onChange={(e) => setAmount(e.target.value)}
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-lg font-mono"
                          placeholder="0.00"
                          required
                          disabled={investing}
                        />
                        <div className="text-xs text-gray-500 mt-1">
                          Max: {maxInvestable.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0 || parseFloat(amount) > maxInvestable || investing || isFull}
                        className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold text-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {investing ? "Processing..." : "Invest"}
                      </button>
                    </form>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Gallery Modal */}
      {showGallery && images.length > 0 && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowGallery(false)}>
          <div className="relative max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowGallery(false)}
              className="absolute top-4 right-4 bg-white/90 text-gray-800 px-4 py-2 rounded-lg hover:bg-white font-medium z-10"
            >
              Close
            </button>
            <img
              src={images[currentImageIndex]?.url || ''}
              alt={`${offer.name} - Image ${currentImageIndex + 1}`}
              className="w-full h-auto rounded-lg"
            />
            {images.length > 1 && (
              <>
                <button
                  onClick={() => setCurrentImageIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1))}
                  className="absolute left-4 top-1/2 -translate-y-1/2 bg-white/90 text-gray-800 p-2 rounded-full hover:bg-white"
                >
                  ←
                </button>
                <button
                  onClick={() => setCurrentImageIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0))}
                  className="absolute right-4 top-1/2 -translate-y-1/2 bg-white/90 text-gray-800 p-2 rounded-full hover:bg-white"
                >
                  →
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Video Modal */}
      {showVideoModal && promoVideo && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={() => setShowVideoModal(false)}>
          <div className="relative max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowVideoModal(false)}
              className="absolute top-4 right-4 bg-white/90 text-gray-800 px-4 py-2 rounded-lg hover:bg-white font-medium z-10"
            >
              Close
            </button>
            {promoVideo.url ? (
              promoVideo.url.includes('youtube.com') || promoVideo.url.includes('youtu.be') || promoVideo.url.includes('vimeo.com') ? (
                <iframe
                  src={promoVideo.url}
                  className="w-full aspect-video rounded-lg"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              ) : (
                <video
                  src={promoVideo.url}
                  controls
                  className="w-full rounded-lg"
                />
              )
            ) : (
              <div className="bg-gray-800 rounded-lg p-8 text-center text-white">
                <p>Video URL not available</p>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  )
}

