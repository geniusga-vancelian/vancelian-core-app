"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import Link from "next/link"
import { getToken, apiRequest, offersApi, articlesApi, partnersApi, type Offer, type InvestInOfferResponse, type ArticleListItem, type PartnerListItem } from "@/lib/api"
import { OfferMediaHero } from "@/components/offers/OfferMediaHero"
import { OfferKpiCard } from "@/components/offers/OfferKpiCard"
import { OfferContentSections } from "@/components/offers/OfferContentSections"
import { OfferInvestCard } from "@/components/offers/OfferInvestCard"

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
  const [relatedOffers, setRelatedOffers] = useState<Offer[]>([])
  const [offerArticles, setOfferArticles] = useState<ArticleListItem[]>([])
  const [offerPartners, setOfferPartners] = useState<PartnerListItem[]>([])
  const [timelineEvents, setTimelineEvents] = useState<Array<{
    id: string
    title: string
    description: string
    occurred_at: string | null
    sort_order: number
    article: { id: string; title: string; slug: string; published_at: string | null; cover_url: string | null } | null
    created_at: string
    updated_at: string | null
  }>>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)

  // Investment
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
      
      // DEBUG: Log media data
      if (process.env.NODE_ENV === 'development') {
        console.log('[OFFER DEBUG] Media data:', {
          hasMedia: !!offerData.media,
          cover: offerData.media?.cover ? { id: offerData.media.cover.id, url: offerData.media.cover.url } : null,
          promoVideo: offerData.media?.promo_video ? { id: offerData.media.promo_video.id, url: offerData.media.promo_video.url } : null,
          galleryCount: offerData.media?.gallery?.length || 0,
          documentsCount: offerData.media?.documents?.length || 0,
        })
      }
      
      setOffer(offerData)

      // Load wallet balance
      const walletResponse = await apiRequest(`api/v1/wallet?currency=${offerData.currency}`)
      if (walletResponse.ok) {
        const walletData = await walletResponse.json()
        setWallet(walletData)
      }

      // Load related offers (exclude current offer)
      try {
        const related = await offersApi.listOffers({ status: 'LIVE', currency: offerData.currency, limit: 6 })
        setRelatedOffers(related.filter(o => o.id !== offerId))
      } catch {
        // Ignore errors for related offers (optional feature)
        setRelatedOffers([])
      }

      // Load articles linked to this offer
      try {
        const articles = await articlesApi.getOfferArticles(offerId, { limit: 3 })
        setOfferArticles(articles)
      } catch {
        // Ignore errors for articles (optional feature)
        setOfferArticles([])
      }

      // Load partners linked to this offer
      try {
        const partners = await partnersApi.getOfferPartners(offerId, { limit: 6 })
        setOfferPartners(partners)
      } catch {
        // Ignore errors for partners (optional feature)
        setOfferPartners([])
      }

      // Load timeline events
      try {
        const timeline = await offersApi.getOfferTimeline(offerId)
        setTimelineEvents(timeline)
      } catch {
        // Ignore errors for timeline (optional feature)
        setTimelineEvents([])
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

  const handleInvest = async (amount: string): Promise<InvestInOfferResponse> => {
    if (!offer) throw new Error("Offer not available")

    const amountNum = parseFloat(amount)
    if (isNaN(amountNum) || amountNum <= 0) {
      throw new Error("Invalid amount")
    }

    const remaining = parseFloat(offer.remaining_amount)
    if (amountNum > remaining) {
      throw new Error(`Maximum available: ${remaining.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${offer.currency}`)
    }

    if (wallet && amountNum > parseFloat(wallet.available_balance)) {
      throw new Error(`Insufficient balance. Available: ${parseFloat(wallet.available_balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${wallet.currency}`)
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

      // Reload after success
      setTimeout(() => {
        loadData()
      }, 1000)

      return result
    } catch (err: any) {
      let errorMessage = err.message || "Investment failed"
      
      if (err.code === 'OFFER_FULL') {
        errorMessage = "Offer is full. Please choose another offer."
      } else if (err.code === 'INSUFFICIENT_FUNDS' || err.code === 'INSUFFICIENT_AVAILABLE_FUNDS') {
        errorMessage = "Insufficient balance for this investment."
      } else if (err.code === 'OFFER_NOT_LIVE' || err.code === 'OFFER_CLOSED') {
        errorMessage = "This offer is no longer available."
      }
      
      setError(errorMessage)
      setTraceId(err.trace_id || null)
      throw err
    } finally {
      setInvesting(false)
    }
  }

  const handleReset = () => {
    setInvestmentResult(null)
    setError(null)
    setTraceId(null)
  }

  // Media is now structured in offer.media (OfferMediaGroup)

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

  return (
    <main className="container mx-auto p-8 max-w-7xl">
      {/* Breadcrumb */}
      <div className="mb-6">
        <nav className="text-sm text-gray-600 mb-2">
          <Link href="/offers" className="hover:text-blue-600">Properties</Link>
          <span className="mx-2">/</span>
          <span className="text-gray-900">{offer.name}</span>
        </nav>
        <Link href="/offers" className="text-blue-600 hover:text-blue-800 inline-flex items-center gap-2 text-sm">
          ← Back to Offers
        </Link>
      </div>

      {/* Hero Media */}
      <OfferMediaHero
        offerName={offer.name}
        media={offer.media}
      />

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
          </div>

          {/* Marketing Content Sections */}
          <OfferContentSections
            offer={offer}
            relatedOffers={relatedOffers}
          />

          {/* Project Progress Timeline */}
          {timelineEvents.length > 0 && (
            <div className="border-t border-gray-200 pt-8">
              <h2 className="text-2xl font-semibold mb-6">Project Progress</h2>
              <div className="relative">
                {/* Timeline line */}
                <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200"></div>
                
                {/* Timeline events */}
                <div className="space-y-6">
                  {timelineEvents.slice(0, 8).map((event, index) => (
                    <div key={event.id} className="relative flex gap-4">
                      {/* Dot */}
                      <div className="relative z-10 flex-shrink-0">
                        <div className="w-8 h-8 rounded-full bg-blue-600 border-4 border-white shadow-md flex items-center justify-center">
                          <div className="w-2 h-2 rounded-full bg-white"></div>
                        </div>
                      </div>
                      
                      {/* Content card */}
                      <div className="flex-1 bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex items-start justify-between gap-4 mb-2">
                          <h3 className="font-semibold text-lg">{event.title}</h3>
                          {event.occurred_at && (
                            <span className="text-sm text-gray-500 whitespace-nowrap">
                              {new Date(event.occurred_at).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                              })}
                            </span>
                          )}
                        </div>
                        <p className="text-gray-700 text-sm mb-3">{event.description}</p>
                        {event.article && (
                          <Link
                            href={`/blog/${event.article.slug}`}
                            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 text-sm font-medium"
                          >
                            Read article →
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              {timelineEvents.length > 8 && (
                <div className="mt-6 text-center">
                  <p className="text-sm text-gray-500">
                    Showing 8 of {timelineEvents.length} updates
                  </p>
                </div>
              )}
            </div>
          )}

          {/* News / Updates Section */}
          {offerArticles.length > 0 && (
            <div className="border-t border-gray-200 pt-8">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-semibold">News & Updates</h2>
                <Link
                  href={`/blog?offer_id=${offerId}`}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  See all →
                </Link>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {offerArticles.map((article) => (
                  <Link
                    key={article.id}
                    href={`/blog/${article.slug}`}
                    className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
                  >
                    {article.cover_url && (
                      <img
                        src={article.cover_url}
                        alt={article.title}
                        className="w-full h-32 object-cover"
                      />
                    )}
                    <div className="p-4">
                      <h3 className="font-semibold mb-2 line-clamp-2 text-sm">{article.title}</h3>
                      <p className="text-xs text-gray-500">
                        {article.published_at
                          ? new Date(article.published_at).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                            })
                          : ''}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {offerArticles.length === 0 && (
            <div className="border-t border-gray-200 pt-8">
              <h2 className="text-2xl font-semibold mb-4">News & Updates</h2>
              <p className="text-gray-500 text-sm">No updates available for this offer yet.</p>
            </div>
          )}

          {/* Trusted Partners Section */}
          {offerPartners.length > 0 && (
            <div className="border-t border-gray-200 pt-8">
              <h2 className="text-2xl font-semibold mb-6">Trusted Partners</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {offerPartners.map((partner) => (
                  <Link
                    key={partner.id}
                    href={`/partners/${partner.code}`}
                    className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
                  >
                    {partner.cover_image_url || partner.ceo_photo_url ? (
                      <img
                        src={partner.cover_image_url || partner.ceo_photo_url}
                        alt={partner.trade_name || partner.legal_name}
                        className="w-full h-32 object-cover"
                      />
                    ) : (
                      <div className="w-full h-32 bg-gray-100 flex items-center justify-center">
                        <span className="text-gray-400 text-sm">No image</span>
                      </div>
                    )}
                    <div className="p-4">
                      <h3 className="font-semibold mb-1 text-sm">{partner.trade_name || partner.legal_name}</h3>
                      {partner.description_markdown && (
                        <p className="text-xs text-gray-600 line-clamp-2 mb-2">
                          {partner.description_markdown.replace(/[#*\[\]()]/g, '').substring(0, 100)}...
                        </p>
                      )}
                      {partner.city && partner.country && (
                        <p className="text-xs text-gray-500">{partner.city}, {partner.country}</p>
                      )}
                      <div className="mt-2 text-blue-600 hover:text-blue-800 text-xs font-medium">
                        View profile →
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Sticky KPI + Invest Module */}
        <div className="lg:col-span-1 space-y-6">
          {/* KPI Card */}
          <OfferKpiCard offer={offer} />

          {/* Invest Card */}
          <OfferInvestCard
            offer={offer}
            wallet={wallet}
            onInvest={handleInvest}
            investing={investing}
            investmentResult={investmentResult}
            error={error}
            traceId={traceId}
            onReset={handleReset}
          />
        </div>
      </div>
    </main>
  )
}

