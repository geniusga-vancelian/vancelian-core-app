"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { getToken, apiRequest, offersApi, type Offer } from "@/lib/api"

interface WalletBalance {
  currency: string
  total_balance: string
  available_balance: string
  blocked_balance: string
  locked_balance: string
}

export default function InvestPage() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [offers, setOffers] = useState<Offer[]>([])
  const [wallet, setWallet] = useState<WalletBalance | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)

  useEffect(() => {
    const checkAuth = () => {
      const authToken = getToken()
      if (!authToken) {
        router.push("/login")
        return
      }
      setToken(authToken)
      loadData()
    }
    checkAuth()
  }, [router])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    setTraceId(null)

    try {
      // Load LIVE offers (status=LIVE in backend)
      const offersData = await offersApi.listOffers({ status: "LIVE", currency: "AED" })
      setOffers(offersData)

      // Load wallet balance
      const walletResponse = await apiRequest('api/v1/wallet?currency=AED')
      if (walletResponse.ok) {
        const walletData = await walletResponse.json()
        setWallet(walletData)
      }
    } catch (err: any) {
      setError(err.message || "Failed to load data")
      setTraceId(err.trace_id || null)

      if (err.status === 401 || err.status === 403) {
        setTimeout(() => router.push('/login'), 2000)
      }
    } finally {
      setLoading(false)
    }
  }

  const getProgressPercentage = (offer: Offer): number => {
    const committed = parseFloat(offer.committed_amount)
    const max = parseFloat(offer.max_amount)
    if (max === 0) return 0
    return Math.min((committed / max) * 100, 100)
  }

  if (loading) {
    return (
      <main className="container mx-auto p-8 max-w-6xl">
        <div className="text-center py-12">
          <p className="text-gray-500">Chargement des offres...</p>
        </div>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8 max-w-6xl">
      <div className="mb-6">
        <Link href="/" className="text-blue-600 hover:underline inline-flex items-center gap-2">
          ← Retour au Dashboard
        </Link>
      </div>

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Investir dans une Offre</h1>
        {wallet && (
          <div className="text-right">
            <div className="text-sm text-gray-600">Solde disponible</div>
            <div className="text-xl font-bold text-green-600">
              {parseFloat(wallet.available_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {wallet.currency}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800 font-medium">{error}</div>
          {traceId && (
            <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
          )}
        </div>
      )}

      {offers.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-lg p-12 text-center">
          <p className="text-gray-500 text-lg">Aucune offre disponible actuellement</p>
          <Link href="/" className="text-blue-600 hover:underline mt-4 inline-block">
            Retour au Dashboard
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {offers.map((offer) => {
            const progress = getProgressPercentage(offer)
            const remaining = parseFloat(offer.remaining_amount)
            const isFull = remaining <= 0

            return (
              <div
                key={offer.id}
                className={`bg-white border rounded-lg p-6 hover:shadow-lg transition-shadow ${
                  isFull ? 'opacity-60' : ''
                }`}
              >
                <div className="flex justify-between items-start mb-3">
                  <h3 className="text-lg font-semibold text-gray-900">{offer.name}</h3>
                  <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                    LIVE
                  </span>
                </div>

                {offer.description && (
                  <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                    {offer.description}
                  </p>
                )}

                {/* Progress Bar */}
                <div className="mb-4">
                  <div className="flex justify-between text-xs text-gray-600 mb-1">
                    <span>Progression</span>
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
                      {parseFloat(offer.committed_amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                    </span>
                    <span>
                      {parseFloat(offer.max_amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                    </span>
                  </div>
                </div>

                {/* Details */}
                <div className="space-y-2 mb-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Restant:</span>
                    <span className={`font-semibold font-mono ${
                      isFull ? 'text-red-600' : 'text-green-600'
                    }`}>
                      {remaining.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                    </span>
                  </div>
                  {offer.maturity_date && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Échéance:</span>
                      <span className="text-gray-900">
                        {new Date(offer.maturity_date).toLocaleDateString('fr-FR')}
                      </span>
                    </div>
                  )}
                </div>

                {/* Action Button */}
                <Link
                  href={`/invest/${offer.id}`}
                  className={`block w-full text-center px-4 py-2 rounded font-medium transition-colors ${
                    isFull
                      ? 'bg-gray-300 text-gray-600 cursor-not-allowed pointer-events-none'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {isFull ? 'Offre complète' : 'Investir'}
                </Link>
              </div>
            )
          })}
        </div>
      )}
    </main>
  )
}
