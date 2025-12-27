'use client'

import { useState, useEffect } from 'react'
import { vaultsApi, VestingTimelineResponse, VestingTimelineItem } from '@/lib/api'

export default function AvenirVestingTimelinePage() {
  const [timeline, setTimeline] = useState<VestingTimelineResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currency, setCurrency] = useState('AED')

  useEffect(() => {
    loadTimeline()
  }, [currency])

  const loadTimeline = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await vaultsApi.getAvenirVestingTimeline(currency)
      setTimeline(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load vesting timeline')
      console.error('Error loading timeline:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatAmount = (amount: string): string => {
    const num = parseFloat(amount)
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num)
  }

  const formatDate = (dateStr: string): string => {
    // Ensure date string is in YYYY-MM-DD format and parse as UTC
    const date = new Date(dateStr + 'T00:00:00Z')
    // Validate date is valid
    if (isNaN(date.getTime())) {
      return dateStr  // Fallback to raw string if invalid
    }
    return new Intl.DateTimeFormat('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      timeZone: 'UTC',
    }).format(date)
  }

  const calculateTotal = (): string => {
    if (!timeline || timeline.items.length === 0) return '0.00'
    const total = timeline.items.reduce((sum, item) => sum + parseFloat(item.amount), 0)
    return total.toFixed(2)
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            AVENIR — Vesting Release Timeline
          </h1>
          <p className="text-gray-600">
            Calendrier des libérations de fonds AVENIR (vesting 365 jours)
          </p>
        </div>

        {/* Currency Selector */}
        <div className="mb-6">
          <label htmlFor="currency" className="block text-sm font-medium text-gray-700 mb-2">
            Devise
          </label>
          <select
            id="currency"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="block w-32 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          >
            <option value="AED">AED</option>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
          </select>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Chargement de la timeline...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Erreur</h3>
                <p className="mt-1 text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Timeline */}
        {!loading && !error && timeline && (
          <>
            {/* Summary */}
            {timeline.items.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Total restant à libérer</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">
                      {formatAmount(calculateTotal())}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-600">Nombre de dates</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">
                      {timeline.items.length}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Empty State */}
            {timeline.items.length === 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                <h3 className="mt-4 text-lg font-medium text-gray-900">Aucune libération à venir</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Vous n'avez pas de fonds AVENIR en cours de vesting.
                </p>
              </div>
            )}

            {/* Timeline Items */}
            {timeline.items.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                <div className="divide-y divide-gray-200">
                  {timeline.items.map((item: VestingTimelineItem, index: number) => (
                    <div
                      key={item.date}
                      className="px-6 py-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        {/* Timeline Line (left side) */}
                        <div className="flex items-center flex-1">
                          <div className="flex-shrink-0 mr-4">
                            <div className="relative">
                              {/* Vertical line */}
                              {index < timeline.items.length - 1 && (
                                <div className="absolute left-1/2 top-6 w-0.5 h-full bg-gray-300 transform -translate-x-1/2"></div>
                              )}
                              {/* Circle */}
                              <div className="relative z-10 w-3 h-3 rounded-full bg-blue-600 border-2 border-white"></div>
                            </div>
                          </div>
                          
                          {/* Date */}
                          <div className="flex-1">
                            <p className="text-lg font-semibold text-gray-900">
                              {formatDate(item.date)}
                            </p>
                            <p className="text-sm text-gray-500 mt-1">
                              {item.date}
                            </p>
                          </div>
                        </div>

                        {/* Amount */}
                        <div className="text-right">
                          <p className="text-xl font-bold text-gray-900">
                            {formatAmount(item.amount)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Refresh Button */}
        {!loading && (
          <div className="mt-6 text-center">
            <button
              onClick={loadTimeline}
              className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <svg
                className="mr-2 h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Actualiser
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

