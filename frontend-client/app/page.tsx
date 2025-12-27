"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { getToken, apiRequest, parseApiError, investmentsApi, depositApi, vaultsApi, type VaultAccountMe, type WithdrawalListItem } from "@/lib/api"
import WalletMatrixCard from "@/components/dev/WalletMatrixCard"

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

interface WalletBalance {
  currency: string
  total_balance: string
  available_balance: string
  blocked_balance: string
  locked_balance: string
}

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

interface InvestmentPosition {
  investment_id: string
  offer_id: string
  offer_code: string
  offer_name: string
  principal: string
  currency: string
  status: string
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
  const [investments, setInvestments] = useState<InvestmentPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<ApiError[]>([])
  const [showBootstrap, setShowBootstrap] = useState(false)
  const [showDepositModal, setShowDepositModal] = useState(false)
  const [depositAmount, setDepositAmount] = useState<string>('')
  const [depositLoading, setDepositLoading] = useState(false)
  const [depositError, setDepositError] = useState<string | null>(null)
  const [depositSuccess, setDepositSuccess] = useState(false)
  
  // Vaults state
  const [flexVault, setFlexVault] = useState<VaultAccountMe | null>(null)
  const [avenirVault, setAvenirVault] = useState<VaultAccountMe | null>(null)
  const [vaultsLoading, setVaultsLoading] = useState(false)
  
  // Vault modals state
  const [showVaultDepositModal, setShowVaultDepositModal] = useState<{ vaultCode: string; vaultName: string } | null>(null)
  const [showVaultWithdrawModal, setShowVaultWithdrawModal] = useState<{ vaultCode: string; vaultName: string } | null>(null)
  const [showVaultWithdrawalsModal, setShowVaultWithdrawalsModal] = useState<{ vaultCode: string; vaultName: string } | null>(null)
  const [vaultWithdrawals, setVaultWithdrawals] = useState<WithdrawalListItem[]>([])
  
  // Vault transaction state
  const [vaultAmount, setVaultAmount] = useState<string>('')
  const [vaultReason, setVaultReason] = useState<string>('')
  const [vaultLoading, setVaultLoading] = useState(false)
  const [vaultError, setVaultError] = useState<string | null>(null)
  const [vaultSuccess, setVaultSuccess] = useState<string | null>(null)

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

      // Load transactions with currency filter
      const transactionsResponse = await apiRequest('api/v1/transactions?currency=AED&limit=20')
      
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

      // Load investment positions
      try {
        const investmentsData = await investmentsApi.list({ currency: 'AED', status: 'ACCEPTED' })
        setInvestments(investmentsData)
      } catch (err: any) {
        // Don't show error for investments if endpoint doesn't exist yet
        console.warn('Failed to load investments:', err)
      }

      // Load vaults
      await loadVaults()
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

  const loadVaults = async () => {
    setVaultsLoading(true)
    try {
      const [flexData, avenirData] = await Promise.all([
        vaultsApi.getMe('FLEX').catch(() => null),
        vaultsApi.getMe('AVENIR').catch(() => null),
      ])
      setFlexVault(flexData)
      setAvenirVault(avenirData)
    } catch (err: any) {
      // Silently fail if vaults don't exist yet
      console.warn('Failed to load vaults:', err)
    } finally {
      setVaultsLoading(false)
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
    process.env.NODE_ENV !== 'production' ||
    process.env.NEXT_PUBLIC_DEV_MODE === 'true' ||
    window.location.hostname === 'localhost' || 
    window.location.hostname === '127.0.0.1'
  )

  const handleDeposit = async () => {
    setDepositLoading(true)
    setDepositError(null)
    setDepositSuccess(false)

    // Validate amount
    const amount = parseFloat(depositAmount)
    if (isNaN(amount) || amount <= 0) {
      setDepositError('Amount must be greater than 0')
      setDepositLoading(false)
      return
    }

    // Format amount to 2 decimals
    const formattedAmount = amount.toFixed(2)

    try {
      // Generate reference with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      const reference = `ZAND-SIM-${timestamp}`

      await depositApi.simulateZandDeposit({
        currency: 'AED',
        amount: formattedAmount,
        reference: reference,
      })

      setDepositSuccess(true)
      setDepositAmount('')
      
      // Close modal and refresh wallet after a short delay
      setTimeout(() => {
        setShowDepositModal(false)
        setDepositSuccess(false)
        loadDashboard()
      }, 1500)
    } catch (err: any) {
      // depositApi.simulateZandDeposit throws an Error object (not a Response)
      // The error already contains message, code, trace_id, status
      const errorMessage = err?.message || 'Failed to process deposit'
      setDepositError(errorMessage)
    } finally {
      setDepositLoading(false)
    }
  }

  const handleVaultDeposit = async () => {
    if (!showVaultDepositModal) return
    
    setVaultLoading(true)
    setVaultError(null)
    setVaultSuccess(null)

    const amount = parseFloat(vaultAmount)
    if (isNaN(amount) || amount <= 0) {
      setVaultError('Amount must be greater than 0')
      setVaultLoading(false)
      return
    }

    const formattedAmount = amount.toFixed(2)

    try {
      await vaultsApi.deposit(showVaultDepositModal.vaultCode, formattedAmount)
      setVaultSuccess('Deposit successful! Refreshing...')
      setVaultAmount('')
      
      setTimeout(() => {
        setShowVaultDepositModal(null)
        setVaultSuccess(null)
        loadDashboard()
      }, 1500)
    } catch (err: any) {
      setVaultError(err?.message || 'Failed to deposit to vault')
    } finally {
      setVaultLoading(false)
    }
  }

  const handleVaultWithdraw = async () => {
    if (!showVaultWithdrawModal) return
    
    setVaultLoading(true)
    setVaultError(null)
    setVaultSuccess(null)

    const amount = parseFloat(vaultAmount)
    if (isNaN(amount) || amount <= 0) {
      setVaultError('Amount must be greater than 0')
      setVaultLoading(false)
      return
    }

    const formattedAmount = amount.toFixed(2)

    try {
      const result = await vaultsApi.withdraw(showVaultWithdrawModal.vaultCode, formattedAmount, vaultReason || undefined)
      
      if (result.status === 'EXECUTED') {
        setVaultSuccess('Withdrawal executed successfully! Refreshing...')
      } else if (result.status === 'PENDING') {
        setVaultSuccess('Withdrawal request queued (pending). Refreshing...')
      }
      
      setVaultAmount('')
      setVaultReason('')
      
      setTimeout(() => {
        setShowVaultWithdrawModal(null)
        setVaultSuccess(null)
        loadDashboard()
      }, 2000)
    } catch (err: any) {
      // Check if it's a LOCKED error
      if (err?.code === 'VAULT_LOCKED' || err?.message?.includes('locked')) {
        setVaultError(err?.message || 'Vault is locked. Cannot withdraw at this time.')
      } else {
        setVaultError(err?.message || 'Failed to withdraw from vault')
      }
    } finally {
      setVaultLoading(false)
    }
  }

  const handleLoadVaultWithdrawals = async (vaultCode: string) => {
    setShowVaultWithdrawalsModal({ vaultCode, vaultName: vaultCode })
    setVaultError(null)
    try {
      const data = await vaultsApi.listWithdrawals(vaultCode)
      setVaultWithdrawals(data.withdrawals)
    } catch (err: any) {
      setVaultError(err?.message || 'Failed to load withdrawals')
    }
  }

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
          <a href="/invest" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Invest in an Offer
          </a>
          <a href="/me" className="text-blue-600 hover:underline">Profile</a>
          <a href="/transactions" className="text-blue-600 hover:underline">All Transactions</a>
          {isDev && (
            <a href="/dev/wallet-matrix" className="text-orange-600 hover:underline text-sm font-semibold">
              🔧 DEV: Wallet Matrix
            </a>
          )}
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
            <div className="flex justify-between items-start mb-1">
              <h3 className="text-sm font-medium text-gray-500">Available</h3>
              {isDev && (
                <button
                  onClick={() => setShowDepositModal(true)}
                  className="bg-green-600 text-white text-xs px-3 py-1 rounded hover:bg-green-700"
                >
                  Deposit
                </button>
              )}
            </div>
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

      {/* Coffres/Vaults Section */}
      <div className="bg-white border border-gray-200 rounded-lg mb-8">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold">Coffres</h2>
        </div>
        {vaultsLoading ? (
          <div className="p-8 text-center text-gray-500">Loading vaults...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
            {/* FLEX Vault Card */}
            {flexVault && (
              <div className="border border-gray-300 rounded-lg p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">{flexVault.vault.name}</h3>
                    <p className="text-sm text-gray-500">Code: {flexVault.vault.code}</p>
                  </div>
                  <span className={`px-2 py-1 text-xs font-semibold rounded ${
                    flexVault.vault.status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
                    flexVault.vault.status === 'PAUSED' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {flexVault.vault.status}
                  </span>
                </div>
                
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Your Principal:</span>
                    <span className="font-semibold">{parseFloat(flexVault.principal).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} AED</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Available Balance:</span>
                    <span className="font-semibold">{parseFloat(flexVault.available_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} AED</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Vault Cash Balance:</span>
                    <span className="text-sm">{parseFloat(flexVault.vault.cash_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} AED</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Total AUM:</span>
                    <span className="text-sm">{parseFloat(flexVault.vault.total_aum).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} AED</span>
                  </div>
                </div>

                <div className="flex gap-2 mb-2">
                  <button
                    onClick={() => setShowVaultDepositModal({ vaultCode: 'FLEX', vaultName: flexVault.vault.name })}
                    className="flex-1 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm"
                  >
                    Deposit
                  </button>
                  <button
                    onClick={() => setShowVaultWithdrawModal({ vaultCode: 'FLEX', vaultName: flexVault.vault.name })}
                    className="flex-1 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
                  >
                    Withdraw
                  </button>
                </div>
                <button
                  onClick={() => handleLoadVaultWithdrawals('FLEX')}
                  className="w-full text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  My withdrawals
                </button>
              </div>
            )}

            {/* AVENIR Vault Card */}
            {avenirVault && (
              <div className="border border-gray-300 rounded-lg p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-lg font-semibold">{avenirVault.vault.name}</h3>
                    <p className="text-sm text-gray-500">Code: {avenirVault.vault.code}</p>
                  </div>
                  <span className={`px-2 py-1 text-xs font-semibold rounded ${
                    avenirVault.vault.status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
                    avenirVault.vault.status === 'PAUSED' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {avenirVault.vault.status}
                  </span>
                </div>
                
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Your Principal:</span>
                    <span className="font-semibold">{parseFloat(avenirVault.principal).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} AED</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Available Balance:</span>
                    <span className="font-semibold">{parseFloat(avenirVault.available_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} AED</span>
                  </div>
                  {avenirVault.locked_until && (
                    <div className="flex justify-between">
                      <span className="text-sm text-gray-600">Locked Until:</span>
                      <span className="text-sm font-semibold text-orange-600">
                        {new Date(avenirVault.locked_until).toLocaleDateString('fr-FR')}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Vault Cash Balance:</span>
                    <span className="text-sm">{parseFloat(avenirVault.vault.cash_balance).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} AED</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Total AUM:</span>
                    <span className="text-sm">{parseFloat(avenirVault.vault.total_aum).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} AED</span>
                  </div>
                </div>

                <div className="flex gap-2 mb-2">
                  <button
                    onClick={() => setShowVaultDepositModal({ vaultCode: 'AVENIR', vaultName: avenirVault.vault.name })}
                    className="flex-1 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm"
                  >
                    Deposit
                  </button>
                  <button
                    onClick={() => setShowVaultWithdrawModal({ vaultCode: 'AVENIR', vaultName: avenirVault.vault.name })}
                    className="flex-1 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
                  >
                    Withdraw
                  </button>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleLoadVaultWithdrawals('AVENIR')}
                    className="flex-1 text-sm text-blue-600 hover:text-blue-800 underline"
                  >
                    My withdrawals
                  </button>
                  <a
                    href="/vaults/avenir/vesting"
                    className="flex-1 text-sm text-blue-600 hover:text-blue-800 underline text-center"
                  >
                    Vesting timeline
                  </a>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Investments/Positions Module */}
      <div className="bg-white border border-gray-200 rounded-lg mb-8">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold">Your Investments</h2>
        </div>
        {investments.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No active investments yet
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Offer</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Principal</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {investments.map((inv) => (
                  <tr key={inv.investment_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{inv.offer_name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500 font-mono">{inv.offer_code}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right font-mono">
                      {parseFloat(inv.principal).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {inv.currency}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-sm ${
                        inv.status === 'ACCEPTED' ? 'bg-green-100 text-green-800' :
                        inv.status === 'REJECTED' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(inv.created_at).toLocaleString('fr-FR')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Wallet Matrix (DEV) */}
      {isDev && <WalletMatrixCard />}

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
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date/Time</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Offer/Product</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {transactions.map((txn) => {
                  const typeLabel = txn.type === 'DEPOSIT' ? 'Dépôt' :
                                   txn.type === 'WITHDRAWAL' ? 'Retrait' :
                                   txn.type === 'INVESTMENT' ? 'Investissement' :
                                   txn.operation_type === 'INVEST_EXCLUSIVE' ? 'Investissement' :
                                   txn.operation_type === 'VAULT_DEPOSIT' ? 'Dépôt Coffre' :
                                   txn.operation_type === 'VAULT_WITHDRAW_EXECUTED' ? 'Retrait Coffre' :
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
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(txn.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
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
                      <td className="px-6 py-4 whitespace-nowrap text-right font-mono">
                        {parseFloat(displayAmount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {txn.currency}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 rounded text-sm ${
                          txn.status === 'AVAILABLE' || txn.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                          txn.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                          txn.status === 'COMPLIANCE_REVIEW' || txn.status === 'LOCKED' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {txn.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
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
      </div>

      {/* Deposit Modal */}
      {showDepositModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Simulate Deposit (DEV)</h2>
            
            {depositSuccess && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
                <p className="text-green-800">Deposit successful! Refreshing balance...</p>
              </div>
            )}
            
            {depositError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                <p className="text-red-800">{depositError}</p>
              </div>
            )}

            <div className="mb-4">
              <label htmlFor="deposit-amount" className="block text-sm font-medium text-gray-700 mb-1">
                Amount (AED)
              </label>
              <input
                id="deposit-amount"
                type="number"
                step="0.01"
                min="0.01"
                value={depositAmount}
                onChange={(e) => setDepositAmount(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="0.00"
                disabled={depositLoading}
              />
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowDepositModal(false)
                  setDepositAmount('')
                  setDepositError(null)
                  setDepositSuccess(false)
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={depositLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleDeposit}
                disabled={depositLoading || !depositAmount}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {depositLoading ? 'Processing...' : 'Confirm Deposit'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Vault Deposit Modal */}
      {showVaultDepositModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Deposit to {showVaultDepositModal.vaultName}</h2>
            
            {vaultSuccess && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
                <p className="text-green-800">{vaultSuccess}</p>
              </div>
            )}
            
            {vaultError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                <p className="text-red-800">{vaultError}</p>
              </div>
            )}

            <div className="mb-4">
              <label htmlFor="vault-deposit-amount" className="block text-sm font-medium text-gray-700 mb-1">
                Amount (AED)
              </label>
              <input
                id="vault-deposit-amount"
                type="number"
                step="0.01"
                min="0.01"
                value={vaultAmount}
                onChange={(e) => setVaultAmount(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="0.00"
                disabled={vaultLoading}
              />
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowVaultDepositModal(null)
                  setVaultAmount('')
                  setVaultError(null)
                  setVaultSuccess(null)
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={vaultLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleVaultDeposit}
                disabled={vaultLoading || !vaultAmount}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {vaultLoading ? 'Processing...' : 'Confirm Deposit'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Vault Withdraw Modal */}
      {showVaultWithdrawModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Withdraw from {showVaultWithdrawModal.vaultName}</h2>
            
            {vaultSuccess && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
                <p className="text-green-800">{vaultSuccess}</p>
              </div>
            )}
            
            {vaultError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                <p className="text-red-800">{vaultError}</p>
              </div>
            )}

            <div className="mb-4">
              <label htmlFor="vault-withdraw-amount" className="block text-sm font-medium text-gray-700 mb-1">
                Amount (AED)
              </label>
              <input
                id="vault-withdraw-amount"
                type="number"
                step="0.01"
                min="0.01"
                value={vaultAmount}
                onChange={(e) => setVaultAmount(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="0.00"
                disabled={vaultLoading}
              />
            </div>

            <div className="mb-4">
              <label htmlFor="vault-withdraw-reason" className="block text-sm font-medium text-gray-700 mb-1">
                Reason (optional)
              </label>
              <input
                id="vault-withdraw-reason"
                type="text"
                value={vaultReason}
                onChange={(e) => setVaultReason(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Reason for withdrawal"
                disabled={vaultLoading}
              />
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowVaultWithdrawModal(null)
                  setVaultAmount('')
                  setVaultReason('')
                  setVaultError(null)
                  setVaultSuccess(null)
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                disabled={vaultLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleVaultWithdraw}
                disabled={vaultLoading || !vaultAmount}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {vaultLoading ? 'Processing...' : 'Confirm Withdraw'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Vault Withdrawals Modal */}
      {showVaultWithdrawalsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">My Withdrawals - {showVaultWithdrawalsModal.vaultName}</h2>
            
            {vaultError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                <p className="text-red-800">{vaultError}</p>
              </div>
            )}

            {vaultWithdrawals.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                No withdrawals found
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Request ID</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created At</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Executed At</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {vaultWithdrawals.map((withdrawal) => (
                      <tr key={withdrawal.request_id}>
                        <td className="px-4 py-3 text-sm font-mono text-gray-900">
                          {withdrawal.request_id.slice(0, 8)}...
                        </td>
                        <td className="px-4 py-3 text-sm text-right font-semibold">
                          {parseFloat(withdrawal.amount).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {withdrawal.currency}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 text-xs font-semibold rounded ${
                            withdrawal.status === 'EXECUTED' ? 'bg-green-100 text-green-800' :
                            withdrawal.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {withdrawal.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {withdrawal.reason || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {new Date(withdrawal.created_at).toLocaleString('fr-FR')}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {withdrawal.executed_at ? new Date(withdrawal.executed_at).toLocaleString('fr-FR') : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => {
                  setShowVaultWithdrawalsModal(null)
                  setVaultWithdrawals([])
                  setVaultError(null)
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
