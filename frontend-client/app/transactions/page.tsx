"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { getToken, getApiUrl } from "@/lib/api"

interface Transaction {
  transaction_id: string
  type: string
  status: string
  amount: string
  currency: string
  created_at: string
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
                <th className="border border-gray-300 p-2 text-left">ID</th>
                <th className="border border-gray-300 p-2 text-left">Type</th>
                <th className="border border-gray-300 p-2 text-left">Statut</th>
                <th className="border border-gray-300 p-2 text-right">Montant</th>
                <th className="border border-gray-300 p-2 text-left">Date</th>
                <th className="border border-gray-300 p-2 text-left">Temps relatif</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((txn) => (
                <tr key={txn.transaction_id} className="hover:bg-gray-50">
                  <td className="border border-gray-300 p-2 font-mono text-sm">
                    {txn.transaction_id.substring(0, 8)}...
                  </td>
                  <td className="border border-gray-300 p-2">
                    <span className={`px-2 py-1 rounded text-sm ${
                      txn.type === 'DEPOSIT' ? 'bg-green-100 text-green-800' :
                      txn.type === 'WITHDRAWAL' ? 'bg-red-100 text-red-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {txn.type}
                    </span>
                  </td>
                  <td className="border border-gray-300 p-2">
                    <span className={`px-2 py-1 rounded text-sm ${
                      txn.status === 'AVAILABLE' ? 'bg-green-100 text-green-800' :
                      txn.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                      txn.status === 'COMPLIANCE_REVIEW' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {txn.status}
                    </span>
                  </td>
                  <td className="border border-gray-300 p-2 text-right font-mono">
                    {parseFloat(txn.amount).toLocaleString('fr-FR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })} {txn.currency}
                  </td>
                  <td className="border border-gray-300 p-2">
                    {formatDate(txn.created_at)}
                  </td>
                  <td className="border border-gray-300 p-2 text-sm text-gray-600">
                    {formatRelativeTime(txn.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}

