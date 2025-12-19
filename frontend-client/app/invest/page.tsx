"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { getToken, apiRequest, parseApiError, offersApi, type Offer, type InvestInOfferResponse } from "@/lib/api"

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
  
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null)
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
      // Load LIVE offers
      const offersData = await offersApi.listOffers({ status: "LIVE", currency: "AED" })
      setOffers(offersData)
      
      // Load wallet balance
      const walletResponse = await apiRequest('api/v1/wallet?currency=AED')
      if (walletResponse.ok) {
        const walletData = await walletResponse.json()
        setWallet(walletData)
      }
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to load data")
      setTraceId(apiError.trace_id || null)
      
      if (err.status === 401 || err.status === 403) {
        setTimeout(() => router.push('/login'), 2000)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleInvest = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedOfferId || !amount) {
      setError("Please select an offer and enter an amount")
      return
    }

    const amountNum = parseFloat(amount)
    if (isNaN(amountNum) || amountNum <= 0) {
      setError("Please enter a valid amount")
      return
    }

    setInvesting(true)
    setError(null)
    setTraceId(null)
    setInvestmentResult(null)

    try {
      // Generate idempotency key
      const idempotencyKey = `invest-${selectedOfferId}-${Date.now()}-${Math.random().toString(36).substring(7)}`
      
      const result = await offersApi.invest(selectedOfferId, {
        amount: amount,
        currency: "AED",
        idempotency_key: idempotencyKey,
      })
      
      setInvestmentResult(result)
      setAmount("")
      
      // Reload wallet and offers after successful investment
      setTimeout(() => {
        loadData()
        // Navigate to dashboard after 3 seconds
        setTimeout(() => {
          router.push("/")
        }, 3000)
      }, 1000)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to invest")
      setTraceId(apiError.trace_id || null)
    } finally {
      setInvesting(false)
    }
  }

  const selectedOffer = offers.find(o => o.id === selectedOfferId)

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Invest in an Offer</h1>
        <p>Loading...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8">
      <div className="mb-6">
        <a href="/" className="text-blue-600 hover:underline">← Back to Dashboard</a>
      </div>

      <h1 className="text-3xl font-bold mb-6">Invest in an Offer</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800">{error}</div>
          {traceId && (
            <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
          )}
        </div>
      )}

      {investmentResult && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <h2 className="text-lg font-semibold text-green-800 mb-2">Investment Successful!</h2>
          <div className="space-y-1 text-sm text-green-700">
            <p>Requested: {parseFloat(investmentResult.requested_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {investmentResult.currency}</p>
            <p>Accepted: {parseFloat(investmentResult.accepted_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {investmentResult.currency}</p>
            {parseFloat(investmentResult.accepted_amount) < parseFloat(investmentResult.requested_amount) && (
              <p className="text-yellow-700 font-semibold">
                ⚠️ Partial fill: Only {parseFloat(investmentResult.accepted_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} was available in the offer.
              </p>
            )}
            <p className="text-xs text-green-600 mt-2">Redirecting to dashboard...</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Offers List */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Available Offers</h2>
          {offers.length === 0 ? (
            <p className="text-gray-500">No LIVE offers available</p>
          ) : (
            <div className="space-y-3">
              {offers.map((offer) => (
                <div
                  key={offer.id}
                  onClick={() => setSelectedOfferId(offer.id)}
                  className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                    selectedOfferId === offer.id
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-semibold">{offer.name}</h3>
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">LIVE</span>
                  </div>
                  {offer.description && (
                    <p className="text-sm text-gray-600 mb-2">{offer.description.substring(0, 100)}...</p>
                  )}
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-500">Remaining:</span>
                      <span className="font-mono ml-1 text-green-600">
                        {parseFloat(offer.remaining_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                      </span>
                    </div>
                    {offer.maturity_date && (
                      <div>
                        <span className="text-gray-500">Maturity:</span>
                        <span className="ml-1">{new Date(offer.maturity_date).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Investment Form */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Investment Details</h2>
          
          {wallet && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
              <div className="text-sm text-gray-600 mb-1">Available Balance</div>
              <div className="text-2xl font-bold text-green-600">
                {parseFloat(wallet.available_balance).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {wallet.currency}
              </div>
            </div>
          )}

          {selectedOffer && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div className="text-sm font-medium text-blue-800 mb-2">Selected Offer: {selectedOffer.name}</div>
              <div className="text-sm text-blue-700">
                <p>Remaining Capacity: {parseFloat(selectedOffer.remaining_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {selectedOffer.currency}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleInvest}>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Investment Amount (AED)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                placeholder="Enter amount"
                required
                disabled={!selectedOfferId || investing}
              />
            </div>

            {selectedOffer && amount && !isNaN(parseFloat(amount)) && parseFloat(amount) > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                <div className="text-sm text-yellow-800">
                  <p className="font-medium">Preview:</p>
                  <p>You will be allocated: {Math.min(parseFloat(amount), parseFloat(selectedOffer.remaining_amount)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {selectedOffer.currency}</p>
                  {parseFloat(amount) > parseFloat(selectedOffer.remaining_amount) && (
                    <p className="text-yellow-700 font-semibold mt-1">
                      ⚠️ Partial fill: Only {parseFloat(selectedOffer.remaining_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} available
                    </p>
                  )}
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={!selectedOfferId || !amount || investing || investmentResult !== null}
              className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {investing ? "Processing..." : "Invest"}
            </button>
          </form>

          {!selectedOfferId && (
            <p className="text-sm text-gray-500 mt-4 text-center">
              Please select an offer from the list
            </p>
          )}
        </div>
      </div>
    </main>
  )
}
