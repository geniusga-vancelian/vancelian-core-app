'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { authApi, walletApi, transactionsApi } from '@/lib/api'

export default function Home() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [hasToken, setHasToken] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [wallet, setWallet] = useState<any>(null)
  const [transactions, setTransactions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const storedToken = sessionStorage.getItem('dev_jwt_token')
    setToken(storedToken)
    setHasToken(!!storedToken)
    
    if (!storedToken) {
      router.push('/login')
      return
    }

    // Fetch user data, wallet, and transactions
    const fetchData = async () => {
      try {
        const [userData, walletData, transactionsData] = await Promise.all([
          authApi.me(),
          walletApi.getBalance('AED'),
          transactionsApi.list(undefined, undefined, 20),
        ])
        setUser(userData)
        setWallet(walletData)
        setTransactions(transactionsData)
      } catch (err) {
        console.error('Failed to fetch data:', err)
        // If 401, redirect to login
        if ((err as any).code === 'HTTP_401') {
          router.push('/login')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [router])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
        <p>Loading...</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
      
      {user && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">User Info</h2>
          <div className="space-y-2">
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>Status:</strong> {user.status}</p>
          </div>
        </div>
      )}

      {wallet && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Wallet Balance ({wallet.currency})</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-2xl font-bold">{wallet.total_balance}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Available</p>
              <p className="text-2xl font-bold text-green-600">{wallet.available_balance}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Blocked</p>
              <p className="text-2xl font-bold text-yellow-600">{wallet.blocked_balance}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Locked</p>
              <p className="text-2xl font-bold text-blue-600">{wallet.locked_balance}</p>
            </div>
          </div>
        </div>
      )}

      {transactions.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Latest Transactions</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {transactions.map((txn) => (
                  <tr key={txn.transaction_id}>
                    <td className="px-4 py-2 text-sm font-mono">{txn.transaction_id.substring(0, 8)}...</td>
                    <td className="px-4 py-2 text-sm">{txn.type}</td>
                    <td className="px-4 py-2 text-sm">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        txn.status === 'AVAILABLE' ? 'bg-green-100 text-green-800' :
                        txn.status === 'COMPLIANCE_REVIEW' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {txn.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-sm">{txn.amount} {txn.currency}</td>
                    <td className="px-4 py-2 text-sm">{new Date(txn.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Available Pages</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="border border-gray-200 rounded p-4">
            <h3 className="font-semibold mb-2">Wallet</h3>
            <p className="text-sm text-gray-600 mb-2">View wallet balances (total, available, blocked, locked)</p>
            <a href="/wallet" className="text-blue-600 text-sm hover:underline">Go to Wallet →</a>
          </div>
          
          <div className="border border-gray-200 rounded p-4">
            <h3 className="font-semibold mb-2">Transactions</h3>
            <p className="text-sm text-gray-600 mb-2">View transaction history</p>
            <a href="/transactions" className="text-blue-600 text-sm hover:underline">Go to Transactions →</a>
          </div>
          
          <div className="border border-gray-200 rounded p-4">
            <h3 className="font-semibold mb-2">Invest</h3>
            <p className="text-sm text-gray-600 mb-2">Create investment intent (lock funds)</p>
            <a href="/invest" className="text-blue-600 text-sm hover:underline">Go to Invest →</a>
          </div>
          
          <div className="border border-gray-200 rounded p-4">
            <h3 className="font-semibold mb-2">Admin / Compliance</h3>
            <p className="text-sm text-gray-600 mb-2">Release or reject deposits (ADMIN/COMPLIANCE/OPS only)</p>
            <a href="/admin/compliance" className="text-blue-600 text-sm hover:underline">Go to Admin →</a>
          </div>
          
          <div className="border border-gray-200 rounded p-4 col-span-2">
            <h3 className="font-semibold mb-2">ZAND Webhook Simulator</h3>
            <p className="text-sm text-gray-600 mb-2">Simulate ZAND bank deposit webhook (generates HMAC signature)</p>
            <a href="/tools/zand-webhook" className="text-blue-600 text-sm hover:underline">Go to ZAND Webhook →</a>
          </div>
        </div>
      </div>
    </div>
  )
}


