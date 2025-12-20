"use client"

import type { Offer } from "@/lib/api"

interface OfferKpiCardProps {
  offer: Offer
  investorsCount?: number
}

export function OfferKpiCard({ offer, investorsCount }: OfferKpiCardProps) {
  const maxAmount = parseFloat(offer.max_amount)
  const committedAmount = parseFloat(offer.committed_amount)
  const progress = maxAmount > 0 ? (committedAmount / maxAmount) * 100 : 0

  // Use Marketing V1.1 metrics from API
  const metrics = offer.marketing_metrics || {}
  const grossYield = metrics.gross_yield !== null && metrics.gross_yield !== undefined 
    ? `${metrics.gross_yield.toFixed(2)}%` 
    : null
  const netYield = metrics.net_yield !== null && metrics.net_yield !== undefined 
    ? `${metrics.net_yield.toFixed(2)}%` 
    : null
  const annualisedReturn = metrics.annualised_return !== null && metrics.annualised_return !== undefined 
    ? `${metrics.annualised_return.toFixed(2)}%` 
    : null
  
  // Use investors_count from metrics if available, otherwise use prop
  const effectiveInvestorsCount = metrics.investors_count !== null && metrics.investors_count !== undefined
    ? metrics.investors_count
    : investorsCount

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
      {/* Price */}
      <div className="mb-6">
        <div className="text-3xl font-bold text-gray-900 mb-2">
          {maxAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
        </div>
        <div className="text-sm text-gray-600">Property price</div>
      </div>

      {/* Progress */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-semibold text-gray-700">Funded</span>
          <span className="text-lg font-bold text-blue-600">{progress.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500">
          <span>{effectiveInvestorsCount !== undefined && effectiveInvestorsCount !== null ? `${effectiveInvestorsCount} investors` : '—'}</span>
          <span>{committedAmount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} / {maxAmount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</span>
        </div>
      </div>

      {/* Yields & Returns */}
      <div className="space-y-3 border-t border-gray-200 pt-4">
        {grossYield ? (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Gross yield</span>
            <span className="text-sm font-semibold text-gray-900">{grossYield}</span>
          </div>
        ) : (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Gross yield</span>
            <span className="text-xs text-gray-400">Coming soon</span>
          </div>
        )}
        
        {netYield ? (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Net yield</span>
            <span className="text-sm font-semibold text-gray-900">{netYield}</span>
          </div>
        ) : (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Net yield</span>
            <span className="text-xs text-gray-400">Coming soon</span>
          </div>
        )}
        
        {annualisedReturn ? (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Annualised return</span>
            <span className="text-sm font-semibold text-green-600">{annualisedReturn}</span>
          </div>
        ) : (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Annualised return</span>
            <span className="text-xs text-gray-400">Coming soon</span>
          </div>
        )}
      </div>

      {/* Help link */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <a href="#" className="text-xs text-blue-600 hover:text-blue-800">
          Need help to understand the details? Learn more
        </a>
      </div>
    </div>
  )
}

