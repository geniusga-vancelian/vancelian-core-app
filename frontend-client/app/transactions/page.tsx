"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { getToken, getApiUrl } from "@/lib/api"

interface Transaction {
  transaction_id: string | null
  operation_id: string | null
  type: string
  operation_type: string | null
  status: string
  amount: string
  currency: string
  created_at: string
  metadata: Record<string, any> | null
  offer_product: string | null
  amount_display?: string | null
  direction?: string | null
  product_label?: string | null
}

// Helper function to safely parse ISO date string
function parseISODate(dateString: string): Date | null {
  if (!dateString) return null
  
  // Handle ISO 8601 format with or without 'Z'
  // Normalize to ensure proper parsing
  let normalized = dateString.trim()
  
  // If it ends with 'Z', it's already UTC
  // If it doesn't have timezone info, assume UTC
  if (!normalized.includes('T')) {
    // Date only, add time
    normalized = normalized + 'T00:00:00Z'
  } else if (!normalized.endsWith('Z') && !normalized.includes('+') && !normalized.includes('-', 10)) {
    // Has T but no timezone, add Z
    normalized = normalized + 'Z'
  }
  
  try {
    const date = new Date(normalized)
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return null
    }
    return date
  } catch {
    return null
  }
}

// Format date for display with locale
function formatDate(dateString: string): string {
  const date = parseISODate(dateString)
  if (!date) {
    return "Date invalide"
  }
  
  // Use toLocaleString for consistent timezone display
  return date.toLocaleString('fr-FR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'UTC', // Display in UTC to match backend
  })
}

// Format relative time (dev-only, no dependencies)
function formatRelativeTime(dateString: string): string {
  const date = parseISODate(dateString)
  if (!date) {
    return ""
  }
  
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)
  
  if (diffSeconds < 60) {
    return `il y a ${diffSeconds}s`
  } else if (diffMinutes < 60) {
    return `il y a ${diffMinutes}min`
  } else if (diffHours < 24) {
    return `il y a ${diffHours}h`
  } else if (diffDays < 7) {
    return `il y a ${diffDays}j`
  } else {
    return formatDate(dateString)
  }
}

export default function TransactionsPage() {
  const router = useRouter()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    const fetchTransactions = async () => {
      const token = getToken()
      if (!token) {
        router.push("/login")
        return
      }

      try {
        const response = await fetch(getApiUrl('api/v1/transactions?limit=50'), {
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        })

        if (!response.ok) {
          if (response.status === 401) {
            router.push("/login")
            return
          }
          const data = await response.json()
          throw new Error(data.detail || "Failed to fetch transactions")
        }

        const data = await response.json()
        setTransactions(data)
      } catch (err: any) {
        setError(err.message || "Failed to load transactions")
      } finally {
        setLoading(false)
      }
    }

    fetchTransactions()
  }, [router])

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-4">Transactions</h1>
        <p>Chargement...</p>
      </main>
    )
  }

  if (error) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-4">Transactions</h1>
        <div className="bg-red-100 text-red-700 p-3 rounded">{error}</div>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Transactions</h1>
        <a href="/" className="text-blue-600 hover:underline">← Retour</a>
      </div>

      {transactions.length === 0 ? (
        <div className="bg-gray-100 p-4 rounded">
          <p>Aucune transaction trouvée.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse border border-gray-300">
            <thead>
              <tr className="bg-gray-100">
                <th className="border border-gray-300 p-2 text-left">Date/Heure</th>
                <th className="border border-gray-300 p-2 text-left">Type</th>
                <th className="border border-gray-300 p-2 text-right">Montant</th>
                <th className="border border-gray-300 p-2 text-left">Statut</th>
                <th className="border border-gray-300 p-2 text-left">Offre/Produit</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((txn) => {
                const typeLabel = txn.type === 'DEPOSIT' ? 'Dépôt' :
                                 txn.type === 'WITHDRAWAL' ? 'Retrait' :
                                 txn.type === 'INVESTMENT' ? 'Investissement' :
                                 txn.operation_type === 'INVEST_EXCLUSIVE' ? 'Investissement' :
  txn.operation_type === 'VAULT_DEPOSIT' ? 'Dépôt Coffre' :
  txn.operation_type === 'VAULT_WITHDRAW_EXECUTED' ? 'Retrait Coffre' :
  txn.operation_type === 'VAULT_VESTING_RELEASE' ? 'Libération Vesting AVENIR' :
                                 txn.type
                // Use amount_display if present (always positive), otherwise fallback to amount
                const displayAmount = txn.amount_display ?? txn.amount
                // Use product_label if present, otherwise fallback to offer_product/metadata
                const productInfo = txn.product_label || txn.offer_product || txn.metadata?.offer_name || txn.metadata?.offer_code
                const txnId = txn.transaction_id || txn.operation_id
                return (
                  <tr
                    key={txnId}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => router.push(`/transactions/${txnId}`)}
                  >
                    <td className="border border-gray-300 p-2 text-sm text-gray-500">
                      {formatDate(txn.created_at)}
                    </td>
                    <td className="border border-gray-300 p-2">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded text-sm ${
                          txn.type === 'DEPOSIT' || txn.operation_type === 'DEPOSIT_AED' ? 'bg-green-100 text-green-800' :
                          txn.type === 'WITHDRAWAL' ? 'bg-red-100 text-red-800' :
                          txn.type === 'INVESTMENT' || txn.operation_type === 'INVEST_EXCLUSIVE' ? 'bg-blue-100 text-blue-800' :
                          txn.operation_type === 'VAULT_DEPOSIT' ? 'bg-green-100 text-green-800' :
                          txn.operation_type === 'VAULT_WITHDRAW_EXECUTED' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {typeLabel}
                        </span>
                        {txn.direction && (
                          <span className={`px-2 py-1 rounded text-xs ${
                            txn.direction === 'IN' ? 'bg-green-100 text-green-700' :
                            txn.direction === 'OUT' ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {txn.direction === 'IN' ? '↓' : '↑'} {txn.direction}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="border border-gray-300 p-2 text-right font-mono">
                      {parseFloat(displayAmount).toLocaleString('fr-FR', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })} {txn.currency}
                    </td>
                    <td className="border border-gray-300 p-2">
                      <span className={`px-2 py-1 rounded text-sm ${
                        txn.status === 'AVAILABLE' || txn.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                        txn.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                        txn.status === 'COMPLIANCE_REVIEW' || txn.status === 'LOCKED' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {txn.status}
                      </span>
                    </td>
                    <td className="border border-gray-300 p-2 text-sm text-gray-500">
                      {productInfo ? (
                        <div>
                          {txn.product_label ? (
                            <div className="font-medium">{txn.product_label}</div>
                          ) : txn.offer_product ? (
                            <div className="font-medium">{txn.offer_product}</div>
                          ) : (
                            <>
                              <div className="font-medium">{txn.metadata?.offer_name}</div>
                              <div className="text-xs text-gray-400 font-mono">{txn.metadata?.offer_code}</div>
                            </>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}

