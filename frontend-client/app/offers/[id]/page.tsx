"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import Link from "next/link"
import { getToken, apiRequest, offersApi, type Offer, type InvestInOfferResponse } from "@/lib/api"
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
          mediaCount: offerData.media?.length || 0,
          media: offerData.media?.map(m => ({ id: m.id, type: m.type, url: m.url, hasUrl: !!m.url })),
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

  const getImages = () => {
    if (!offer?.media) return []
    return offer.media.filter(m => m.type === 'IMAGE').sort((a, b) => a.sort_order - b.sort_order)
  }

  const getPromoVideo = () => {
    if (!offer?.media) return null
    return offer.media.find(m => m.type === 'VIDEO') || null
  }

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
        images={images}
        promoVideo={promoVideo}
        offerId={offerId}
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

