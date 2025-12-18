"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { getToken, apiRequest, parseApiError } from "@/lib/api"

interface WalletBalance {
  currency: string
  total_balance: string
  available_balance: string
  blocked_balance: string
  locked_balance: string
}

interface Transaction {
  transaction_id: string
  type: string
  status: string
  amount: string
  currency: string
  created_at: string
}

interface ApiError {
  endpoint: string
  status: number
  code?: string
  message: string
  trace_id?: string
}

export default function Dashboard() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [wallet, setWallet] = useState<WalletBalance | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<ApiError[]>([])
  const [showBootstrap, setShowBootstrap] = useState(false)

  useEffect(() => {
    const checkAuth = () => {
      const authToken = getToken()
      if (!authToken) {
        router.push("/login")
        return
      }
      setToken(authToken)
      loadDashboard()
    }
    checkAuth()
  }, [router])

  const loadDashboard = async () => {
    setLoading(true)
    setErrors([])
    setShowBootstrap(false)

    try {
      // Load wallet balance
      const walletResponse = await apiRequest('api/v1/wallet?currency=AED')
      
      if (!walletResponse.ok) {
        const error = await parseApiError(walletResponse)
        setErrors(prev => [...prev, {
          endpoint: 'GET /api/v1/wallet',
          status: walletResponse.status,
          ...error,
        }])
        
        // Check if it's a missing account error
        if (walletResponse.status === 404 || error.code === 'ACCOUNT_NOT_FOUND') {
          setShowBootstrap(true)
        }
        
        // Redirect on 401/403
        if (walletResponse.status === 401 || walletResponse.status === 403) {
          setTimeout(() => router.push('/login'), 2000)
        }
      } else {
        const walletData = await walletResponse.json()
        setWallet(walletData)
      }

      // Load transactions (no currency param - backend doesn't support it)
      const transactionsResponse = await apiRequest('api/v1/transactions?limit=20')
      
      if (!transactionsResponse.ok) {
        const error = await parseApiError(transactionsResponse)
        setErrors(prev => [...prev, {
          endpoint: 'GET /api/v1/transactions',
          status: transactionsResponse.status,
          ...error,
        }])
        
        // Redirect on 401/403
        if (transactionsResponse.status === 401 || transactionsResponse.status === 403) {
          setTimeout(() => router.push('/login'), 2000)
        }
      } else {
        const transactionsData = await transactionsResponse.json()
        setTransactions(transactionsData)
      }
    } catch (err: any) {
      setErrors(prev => [...prev, {
        endpoint: 'Dashboard load',
        status: 0,
        message: err.message || 'Network error',
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleBootstrap = async () => {
    try {
      // Try DEV bootstrap endpoint
      const response = await apiRequest('dev/v1/bootstrap/user', {
        method: 'POST',
      })
      
      if (response.ok) {
        setShowBootstrap(false)
        loadDashboard()
      } else {
        const error = await parseApiError(response)
        alert(`Bootstrap failed: ${error.message}`)
      }
    } catch (err: any) {
      alert(`Bootstrap error: ${err.message}`)
    }
  }

  const isDev = typeof window !== 'undefined' && (
    window.location.hostname === 'localhost' || 
    window.location.hostname === '127.0.0.1'
  )

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-4">Dashboard</h1>
        <p>Loading...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="space-x-4">
          <a href="/me" className="text-blue-600 hover:underline">Profile</a>
          <a href="/transactions" className="text-blue-600 hover:underline">All Transactions</a>
        </div>
      </div>

      {/* Error Panel */}
      {errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <h2 className="text-lg font-semibold text-red-800 mb-2">API Errors</h2>
          {errors.map((error, idx) => (
            <div key={idx} className="mb-2 text-sm">
              <div className="font-mono text-red-700">{error.endpoint}</div>
              <div className="text-red-600">
                Status: {error.status} | Code: {error.code || 'N/A'} | {error.message}
              </div>
              {error.trace_id && (
                <div className="text-xs text-red-500 font-mono mt-1">Trace ID: {error.trace_id}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Bootstrap Helper (DEV only) */}
      {showBootstrap && isDev && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <h2 className="text-lg font-semibold text-yellow-800 mb-2">DEV: Missing AED Accounts</h2>
          <p className="text-yellow-700 mb-3">
            Your user has no AED accounts yet. Use the button below to create them (DEV only).
          </p>
          <button
            onClick={handleBootstrap}
            className="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700"
          >
            Create AED Accounts (DEV)
          </button>
        </div>
      )}

      {/* Wallet Cards */}
      {wallet && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-1">Total Balance</h3>
            <p className="text-2xl font-bold">{parseFloat(wallet.total_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {wallet.currency}</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-1">Available</h3>
            <p className="text-2xl font-bold text-green-600">{parseFloat(wallet.available_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {wallet.currency}</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-1">Under Review</h3>
            <p className="text-2xl font-bold text-yellow-600">{parseFloat(wallet.blocked_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {wallet.currency}</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-1">Invested</h3>
            <p className="text-2xl font-bold text-blue-600">{parseFloat(wallet.locked_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {wallet.currency}</p>
          </div>
        </div>
      )}

      {/* Transactions List */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold">Latest Transactions</h2>
        </div>
        {transactions.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No transactions yet
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {transactions.map((txn) => (
                  <tr key={txn.transaction_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-sm ${
                        txn.type === 'DEPOSIT' ? 'bg-green-100 text-green-800' :
                        txn.type === 'WITHDRAWAL' ? 'bg-red-100 text-red-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {txn.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-sm ${
                        txn.status === 'AVAILABLE' ? 'bg-green-100 text-green-800' :
                        txn.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                        txn.status === 'COMPLIANCE_REVIEW' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {txn.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right font-mono">
                      {parseFloat(txn.amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {txn.currency}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(txn.created_at).toLocaleString('fr-FR')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  )
}
