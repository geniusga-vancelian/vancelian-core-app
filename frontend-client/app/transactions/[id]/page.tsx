'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { transactionsApi, TransactionDetail } from '@/lib/api'
import { getToken } from '@/lib/api'
import { formatDateTime, formatRelativeTime } from '@/lib/format'
import CopyButton from '@/components/CopyButton'
import Timeline from '@/components/Timeline'

export default function TransactionDetailPage() {
  const router = useRouter()
  const params = useParams()
  const transactionId = params.id as string

  const [transaction, setTransaction] = useState<TransactionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showRawJson, setShowRawJson] = useState(false)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      router.push('/login')
      return
    }

    const fetchTransaction = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await transactionsApi.getById(transactionId)
        setTransaction(data)
      } catch (err: any) {
        setError(err.message || 'Failed to load transaction')
        if (err.status === 404) {
          setError('Transaction not found')
        }
      } finally {
        setLoading(false)
      }
    }

    if (transactionId) {
      fetchTransaction()
    }
  }, [transactionId, router])

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <div className="text-center py-12">
          <p className="text-gray-500">Chargement...</p>
        </div>
      </main>
    )
  }

  if (error || !transaction) {
    return (
      <main className="container mx-auto p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-red-800">{error || 'Transaction not found'}</p>
        </div>
        <a href="/transactions" className="text-blue-600 hover:underline">
          ← Retour aux transactions
        </a>
      </main>
    )
  }

  // Build timeline items
  const timelineItems = []
  timelineItems.push({
    label: 'Créée',
    status: 'completed' as const,
    timestamp: transaction.created_at,
  })

  if (transaction.status === 'COMPLIANCE_REVIEW') {
    timelineItems.push({
      label: 'En révision de conformité',
      status: 'active' as const,
      timestamp: transaction.updated_at || transaction.created_at,
    })
  } else if (transaction.status === 'LOCKED') {
    timelineItems.push({
      label: 'Fonds verrouillés',
      status: 'active' as const,
      timestamp: transaction.updated_at || transaction.created_at,
    })
  } else if (transaction.status === 'AVAILABLE' || transaction.status === 'COMPLETED') {
    timelineItems.push({
      label: 'Disponible',
      status: 'completed' as const,
      timestamp: transaction.updated_at || transaction.created_at,
    })
  } else if (transaction.status === 'FAILED' || transaction.status === 'REJECTED') {
    timelineItems.push({
      label: 'Échouée',
      status: 'failed' as const,
      timestamp: transaction.updated_at || transaction.created_at,
    })
  }

  // Get type label
  const typeLabel =
    transaction.type === 'DEPOSIT'
      ? 'Dépôt'
      : transaction.type === 'WITHDRAWAL'
      ? 'Retrait'
      : transaction.type === 'INVESTMENT'
      ? 'Investissement'
      : transaction.type

  // Get status label
  const statusLabel =
    transaction.status === 'AVAILABLE'
      ? 'Disponible'
      : transaction.status === 'COMPLIANCE_REVIEW'
      ? 'En révision'
      : transaction.status === 'LOCKED'
      ? 'Verrouillé'
      : transaction.status === 'FAILED'
      ? 'Échoué'
      : transaction.status === 'CANCELLED'
      ? 'Annulé'
      : transaction.status

  // Get status color
  const statusColor =
    transaction.status === 'AVAILABLE' || transaction.status === 'COMPLETED'
      ? 'bg-green-100 text-green-800'
      : transaction.status === 'FAILED' || transaction.status === 'REJECTED'
      ? 'bg-red-100 text-red-800'
      : transaction.status === 'COMPLIANCE_REVIEW' || transaction.status === 'LOCKED'
      ? 'bg-yellow-100 text-yellow-800'
      : 'bg-gray-100 text-gray-800'

  // Get type color
  const typeColor =
    transaction.type === 'DEPOSIT'
      ? 'bg-green-100 text-green-800'
      : transaction.type === 'WITHDRAWAL'
      ? 'bg-red-100 text-red-800'
      : transaction.type === 'INVESTMENT'
      ? 'bg-blue-100 text-blue-800'
      : 'bg-gray-100 text-gray-800'

  return (
    <main className="container mx-auto p-8 max-w-4xl">
      {/* Navigation */}
      <div className="mb-6">
        <a
          href="/transactions"
          className="text-blue-600 hover:underline inline-flex items-center gap-2"
        >
          ← Retour aux transactions
        </a>
      </div>

      {/* Header Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="text-4xl font-bold mb-2">
              {parseFloat(transaction.amount).toLocaleString('fr-FR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{' '}
              {transaction.currency}
            </div>
            <div className="flex items-center gap-3 mb-2">
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${typeColor}`}>
                {typeLabel}
              </span>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${statusColor}`}>
                {statusLabel}
              </span>
            </div>
            <div className="text-sm text-gray-500">
              {formatDateTime(transaction.created_at)}
              {formatRelativeTime(transaction.created_at) && (
                <span className="ml-2">({formatRelativeTime(transaction.created_at)})</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Timeline Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Timeline</h2>
        <Timeline items={timelineItems} />
      </div>

      {/* Core Details Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Détails</h2>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700">Transaction ID</label>
            <CopyButton value={transaction.id} className="mt-1" />
          </div>
          {transaction.operation_id && (
            <div>
              <label className="text-sm font-medium text-gray-700">Operation ID</label>
              <CopyButton value={transaction.operation_id} className="mt-1" />
            </div>
          )}
          {transaction.trace_id && (
            <div>
              <label className="text-sm font-medium text-gray-700">Trace ID</label>
              <CopyButton value={transaction.trace_id} className="mt-1" />
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Devise</label>
              <div className="mt-1 text-sm">{transaction.currency}</div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Montant</label>
              <div className="mt-1 text-sm font-mono">
                {parseFloat(transaction.amount).toLocaleString('fr-FR', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Type</label>
              <div className="mt-1 text-sm">{typeLabel}</div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Statut</label>
              <div className="mt-1 text-sm">{statusLabel}</div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Créée le</label>
              <div className="mt-1 text-sm">{formatDateTime(transaction.created_at)}</div>
            </div>
            {transaction.updated_at && (
              <div>
                <label className="text-sm font-medium text-gray-700">Modifiée le</label>
                <div className="mt-1 text-sm">{formatDateTime(transaction.updated_at)}</div>
              </div>
            )}
          </div>
          {transaction.user_email && (
            <div>
              <label className="text-sm font-medium text-gray-700">Email</label>
              <div className="mt-1 text-sm">{transaction.user_email}</div>
            </div>
          )}
        </div>
      </div>

      {/* Wallet Movement Card */}
      {transaction.movement && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Mouvement de portefeuille</h2>
          <div className="flex items-center gap-4">
            <div className="px-4 py-2 bg-gray-100 rounded">
              <div className="text-sm text-gray-600">De</div>
              <div className="font-semibold">{transaction.movement.from_bucket}</div>
            </div>
            <div className="text-2xl text-gray-400">→</div>
            <div className="px-4 py-2 bg-gray-100 rounded">
              <div className="text-sm text-gray-600">Vers</div>
              <div className="font-semibold">{transaction.movement.to_bucket}</div>
            </div>
            <div className="ml-auto text-lg font-semibold">
              {parseFloat(transaction.amount).toLocaleString('fr-FR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{' '}
              {transaction.currency}
            </div>
          </div>
        </div>
      )}

      {/* Related Context Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Contexte / Liens</h2>
        {transaction.metadata && Object.keys(transaction.metadata).length > 0 ? (
          <div className="space-y-4">
            {transaction.metadata.offer_id && (
              <div>
                <label className="text-sm font-medium text-gray-700">Offer ID</label>
                <CopyButton value={transaction.metadata.offer_id} className="mt-1" />
              </div>
            )}
            {transaction.metadata.offer_code && (
              <div>
                <label className="text-sm font-medium text-gray-700">Offer Code</label>
                <CopyButton value={transaction.metadata.offer_code} className="mt-1" />
              </div>
            )}
            {transaction.metadata.offer_name && (
              <div>
                <label className="text-sm font-medium text-gray-700">Offer Name</label>
                <div className="mt-1 text-sm">{transaction.metadata.offer_name}</div>
              </div>
            )}
            {transaction.metadata.investment_id && (
              <div>
                <label className="text-sm font-medium text-gray-700">Investment ID</label>
                <CopyButton value={transaction.metadata.investment_id} className="mt-1" />
              </div>
            )}
            {transaction.metadata.idempotency_key && (
              <div>
                <label className="text-sm font-medium text-gray-700">Idempotency Key</label>
                <CopyButton value={transaction.metadata.idempotency_key} className="mt-1" />
              </div>
            )}
            {transaction.metadata.provider_event_id && (
              <div>
                <label className="text-sm font-medium text-gray-700">Provider Event ID</label>
                <CopyButton value={transaction.metadata.provider_event_id} className="mt-1" />
              </div>
            )}
            {transaction.metadata.iban && (
              <div>
                <label className="text-sm font-medium text-gray-700">IBAN</label>
                <CopyButton
                  value={transaction.metadata.iban}
                  label={maskIban(transaction.metadata.iban)}
                  className="mt-1"
                />
              </div>
            )}
          </div>
        ) : (
          <div className="text-gray-500 text-sm">Aucun contexte lié</div>
        )}
      </div>

      {/* Raw JSON Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">JSON brut</h2>
          <button
            onClick={() => setShowRawJson(!showRawJson)}
            className="text-sm text-blue-600 hover:underline"
          >
            {showRawJson ? 'Masquer' : 'Afficher'}
          </button>
        </div>
        {showRawJson && (
          <div className="relative">
            <pre className="bg-gray-50 p-4 rounded text-xs overflow-x-auto">
              {JSON.stringify(transaction, null, 2)}
            </pre>
            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(JSON.stringify(transaction, null, 2))
                  alert('JSON copié dans le presse-papiers')
                } catch (err) {
                  console.error('Failed to copy:', err)
                }
              }}
              className="mt-2 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Copier JSON
            </button>
          </div>
        )}
      </div>
    </main>
  )
}

function maskIban(iban: string): string {
  if (!iban || iban.length < 8) return iban
  return iban.slice(0, 4) + '****' + iban.slice(-4)
}

