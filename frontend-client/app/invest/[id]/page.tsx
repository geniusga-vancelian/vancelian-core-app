"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import Link from "next/link"
import { getToken, apiRequest, parseApiError, offersApi, type Offer, type InvestInOfferResponse } from "@/lib/api"

interface WalletBalance {
  currency: string
  total_balance: string
  available_balance: string
  blocked_balance: string
  locked_balance: string
}

export default function InvestDetailPage() {
  const router = useRouter()
  const params = useParams()
  const offerId = params.id as string

  const [offer, setOffer] = useState<Offer | null>(null)
  const [wallet, setWallet] = useState<WalletBalance | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)

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
      const walletResponse = await apiRequest('api/v1/wallet?currency=AED')
      if (walletResponse.ok) {
        const walletData = await walletResponse.json()
        setWallet(walletData)
      }
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to load offer")
      setTraceId(apiError.trace_id || null)

      if (err.status === 401 || err.status === 403) {
        setTimeout(() => router.push('/login'), 2000)
      } else if (err.status === 404) {
        setError("Offre non trouvée")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleInvest = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!amount) {
      setError("Veuillez entrer un montant")
      return
    }

    const amountNum = parseFloat(amount)
    if (isNaN(amountNum) || amountNum <= 0) {
      setError("Montant invalide")
      return
    }

    if (!offer) {
      setError("Offre non disponible")
      return
    }

    const remaining = parseFloat(offer.remaining_amount)
    if (amountNum > remaining) {
      setError(`Montant maximum disponible: ${remaining.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${offer.currency}`)
      return
    }

    if (wallet && amountNum > parseFloat(wallet.available_balance)) {
      setError(`Solde insuffisant. Disponible: ${parseFloat(wallet.available_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${wallet.currency}`)
      return
    }

    setInvesting(true)
    setError(null)
    setTraceId(null)
    setInvestmentResult(null)

    try {
      // Generate idempotency key
      const idempotencyKey = `invest-${offerId}-${Date.now()}-${Math.random().toString(36).substring(7)}`

      const result = await offersApi.invest(offerId, {
        amount: amount,
        currency: offer.currency,
        idempotency_key: idempotencyKey,
      })

      setInvestmentResult(result)
      setAmount("")

      // Reload offer and wallet after successful investment
      setTimeout(() => {
        loadData()
      }, 1000)
    } catch (err: any) {
      const apiError = parseApiError(err)
      
      // Handle specific error codes
      if (apiError.code === 'OFFER_FULL') {
        setError("L'offre est complète. Veuillez choisir une autre offre.")
      } else if (apiError.code === 'INSUFFICIENT_FUNDS') {
        setError("Solde insuffisant pour cet investissement.")
      } else if (apiError.code === 'OFFER_NOT_LIVE') {
        setError("Cette offre n'est plus disponible.")
      } else {
        setError(apiError.message || "Échec de l'investissement")
      }
      
      setTraceId(apiError.trace_id || null)
    } finally {
      setInvesting(false)
    }
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

  const isValidAmount = (): boolean => {
    if (!amount) return false
    const amountNum = parseFloat(amount)
    if (isNaN(amountNum) || amountNum <= 0) return false
    const maxInvestable = getMaxInvestable()
    return amountNum <= maxInvestable
  }

  if (loading) {
    return (
      <main className="container mx-auto p-8 max-w-4xl">
        <div className="text-center py-12">
          <p className="text-gray-500">Chargement...</p>
        </div>
      </main>
    )
  }

  if (!offer) {
    return (
      <main className="container mx-auto p-8 max-w-4xl">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error || "Offre non trouvée"}</p>
        </div>
        <Link href="/invest" className="text-blue-600 hover:underline">
          ← Retour aux offres
        </Link>
      </main>
    )
  }

  const progress = getProgressPercentage()
  const remaining = parseFloat(offer.remaining_amount)
  const isFull = remaining <= 0
  const maxInvestable = getMaxInvestable()

  return (
    <main className="container mx-auto p-8 max-w-4xl">
      <div className="mb-6">
        <Link href="/invest" className="text-blue-600 hover:underline inline-flex items-center gap-2">
          ← Retour aux offres
        </Link>
      </div>

      {/* Offer Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">{offer.name}</h1>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 text-sm font-semibold rounded-full bg-green-100 text-green-800">
                LIVE
              </span>
              <span className="text-sm text-gray-500 font-mono">{offer.code}</span>
            </div>
          </div>
        </div>

        {offer.description && (
          <p className="text-gray-700 mb-6">{offer.description}</p>
        )}

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Progression de l'offre</span>
            <span className="font-semibold">{progress.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between text-sm">
            <div>
              <span className="text-gray-600">Engagé: </span>
              <span className="font-semibold font-mono">
                {parseFloat(offer.committed_amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Maximum: </span>
              <span className="font-semibold font-mono">
                {parseFloat(offer.max_amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
              </span>
            </div>
          </div>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Restant:</span>
            <span className={`ml-2 font-semibold font-mono ${
              isFull ? 'text-red-600' : 'text-green-600'
            }`}>
              {remaining.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
            </span>
          </div>
          {offer.maturity_date && (
            <div>
              <span className="text-gray-600">Échéance:</span>
              <span className="ml-2 font-semibold">
                {new Date(offer.maturity_date).toLocaleDateString('fr-FR', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Error Message */}
      {error && !investmentResult && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800 font-medium">{error}</div>
          {traceId && (
            <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
          )}
        </div>
      )}

      {/* Success Message */}
      {investmentResult && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-green-800 mb-4">✅ Investissement réussi!</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-700">Montant demandé:</span>
              <span className="font-semibold font-mono">
                {parseFloat(investmentResult.requested_amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {investmentResult.currency}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-700">Montant accepté:</span>
              <span className="font-semibold font-mono text-green-600">
                {parseFloat(investmentResult.accepted_amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {investmentResult.currency}
              </span>
            </div>
            {parseFloat(investmentResult.accepted_amount) < parseFloat(investmentResult.requested_amount) && (
              <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mt-3">
                <p className="text-yellow-800 font-semibold text-sm">
                  ⚠️ Remplissage partiel: Seulement {parseFloat(investmentResult.accepted_amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {investmentResult.currency} était disponible dans l'offre.
                </p>
              </div>
            )}
            <div className="flex justify-between mt-4 pt-4 border-t border-green-200">
              <span className="text-gray-700">Restant après investissement:</span>
              <span className="font-semibold font-mono">
                {parseFloat(investmentResult.offer_remaining_amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {investmentResult.currency}
              </span>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <Link
              href="/"
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
            >
              Retour au Dashboard
            </Link>
            <button
              onClick={() => {
                setInvestmentResult(null)
                setAmount("")
                loadData()
              }}
              className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300 text-sm"
            >
              Investir à nouveau
            </button>
          </div>
        </div>
      )}

      {/* Investment Form */}
      {!investmentResult && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Investir</h2>

          {/* Available Balance */}
          {wallet && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
              <div className="text-sm text-gray-600 mb-1">Solde disponible</div>
              <div className="text-2xl font-bold text-green-600">
                {parseFloat(wallet.available_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {wallet.currency}
              </div>
            </div>
          )}

          {/* Max Investable Warning */}
          {wallet && maxInvestable < remaining && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-yellow-800">
                ⚠️ Votre solde disponible limite votre investissement à {maxInvestable.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
              </p>
            </div>
          )}

          {isFull ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
              <p className="text-red-800 font-semibold">Cette offre est complète</p>
              <Link href="/invest" className="text-blue-600 hover:underline mt-2 inline-block">
                Voir les autres offres
              </Link>
            </div>
          ) : (
            <form onSubmit={handleInvest}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Montant ({offer.currency})
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
                  Maximum: {maxInvestable.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                </div>
              </div>

              {/* Preview */}
              {amount && !isNaN(parseFloat(amount)) && parseFloat(amount) > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                  <div className="text-sm font-medium text-blue-800 mb-2">Aperçu</div>
                  <div className="space-y-1 text-sm text-blue-700">
                    <div className="flex justify-between">
                      <span>Montant demandé:</span>
                      <span className="font-mono font-semibold">{parseFloat(amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Montant accepté (estimé):</span>
                      <span className="font-mono font-semibold">
                        {Math.min(parseFloat(amount), remaining).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                      </span>
                    </div>
                    {parseFloat(amount) > remaining && (
                      <div className="mt-2 pt-2 border-t border-blue-200">
                        <p className="text-yellow-700 font-semibold text-xs">
                          ⚠️ Remplissage partiel: Seulement {remaining.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency} disponible
                        </p>
                      </div>
                    )}
                    {wallet && parseFloat(amount) > parseFloat(wallet.available_balance) && (
                      <div className="mt-2 pt-2 border-t border-blue-200">
                        <p className="text-red-700 font-semibold text-xs">
                          ⚠️ Solde insuffisant
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={!isValidAmount() || investing || isFull}
                className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold text-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {investing ? "Traitement..." : "Investir"}
              </button>

              {!isValidAmount() && amount && (
                <p className="text-sm text-red-600 mt-2 text-center">
                  {parseFloat(amount) > maxInvestable
                    ? `Montant maximum: ${maxInvestable.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${offer.currency}`
                    : "Montant invalide"}
                </p>
              )}
            </form>
          )}
        </div>
      )}
    </main>
  )
}

