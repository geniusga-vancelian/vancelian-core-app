"use client"

import { useState } from "react"
import type { Offer, InvestInOfferResponse } from "@/lib/api"

interface WalletBalance {
  currency: string
  available_balance: string
}

interface OfferInvestCardProps {
  offer: Offer
  wallet: WalletBalance | null
  onInvest: (amount: string) => Promise<InvestInOfferResponse>
  investing: boolean
  investmentResult: InvestInOfferResponse | null
  error: string | null
  traceId: string | null
  onReset: () => void
}

export function OfferInvestCard({
  offer,
  wallet,
  onInvest,
  investing,
  investmentResult,
  error,
  traceId,
  onReset,
}: OfferInvestCardProps) {
  const [amount, setAmount] = useState("")

  const remaining = parseFloat(offer.remaining_amount)
  const isFull = remaining <= 0
  const maxInvestable = wallet
    ? Math.min(remaining, parseFloat(wallet.available_balance))
    : remaining

  const quickAmounts = offer.currency === 'AED' ? [2000, 3000, 5000, 10000] : []

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) return
    if (parseFloat(amount) > maxInvestable) return
    await onInvest(amount)
  }

  const isValidAmount = (): boolean => {
    if (!amount) return false
    const amountNum = parseFloat(amount)
    if (isNaN(amountNum) || amountNum <= 0) return false
    return amountNum <= maxInvestable
  }

  return (
    <div className="sticky top-8">
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-lg">
        <h2 className="text-xl font-semibold mb-4">Invest Now</h2>

        {/* Available Balance */}
        {wallet && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
            <div className="text-sm text-gray-600 mb-1">Amount from wallet</div>
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
                <span className="text-gray-700">You requested:</span>
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
              <div className="flex justify-between mt-3 pt-3 border-t border-green-200">
                <span className="text-gray-700">Remaining:</span>
                <span className="font-mono font-semibold">
                  {parseFloat(investmentResult.offer_remaining_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {investmentResult.currency}
                </span>
              </div>
            </div>
            <button
              onClick={() => {
                onReset()
                setAmount("")
              }}
              className="mt-3 w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm font-medium transition-colors"
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
              <form onSubmit={handleSubmit}>
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
                          className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm font-medium transition-colors"
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
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg text-lg font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
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
                  disabled={!isValidAmount() || investing || isFull}
                  className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold text-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                  {investing ? (
                    <>
                      <span className="animate-spin">⏳</span>
                      Processing...
                    </>
                  ) : (
                    <>
                      ⚡ Invest Now
                    </>
                  )}
                </button>

                {!isValidAmount() && amount && (
                  <p className="text-sm text-red-600 mt-2 text-center">
                    {parseFloat(amount) > maxInvestable
                      ? `Maximum: ${maxInvestable.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${offer.currency}`
                      : "Invalid amount"}
                  </p>
                )}
              </form>
            )}
          </>
        )}
      </div>
    </div>
  )
}

