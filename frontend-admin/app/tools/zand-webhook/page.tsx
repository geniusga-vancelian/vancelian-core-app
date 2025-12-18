"use client"

import { useState, useEffect } from "react"
import { getApiUrl, adminApi, parseApiError } from "@/lib/api"

interface User {
  user_id: string
  email: string
  first_name?: string
  last_name?: string
  status: string
  created_at: string
}

export default function ZandWebhookPage() {
  // User selection
  const [users, setUsers] = useState<User[]>([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [usersError, setUsersError] = useState("")
  const [userSearch, setUserSearch] = useState("")
  const [selectedUser, setSelectedUser] = useState<User | null>(null)

  // Form fields
  const [amount, setAmount] = useState("1000.00")
  const [currency, setCurrency] = useState("AED")
  const [providerEventId, setProviderEventId] = useState("")
  const [iban, setIban] = useState("AE123456789012345678901")

  // Advanced JSON
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [jsonPayload, setJsonPayload] = useState("")

  // Response
  const [response, setResponse] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<{ message: string; code?: string; trace_id?: string } | null>(null)
  const [success, setSuccess] = useState(false)

  // Load users on mount
  useEffect(() => {
    fetchUsers()
  }, [])

  // Auto-generate provider_event_id if empty
  useEffect(() => {
    if (!providerEventId) {
      const timestamp = Date.now()
      const random = Math.floor(Math.random() * 10000)
      setProviderEventId(`ZAND-EVT-${timestamp}-${random}`)
    }
  }, [providerEventId])

  // Update JSON payload when form changes
  useEffect(() => {
    if (selectedUser) {
      const payload = {
        provider_event_id: providerEventId || `ZAND-EVT-${Date.now()}`,
        iban: iban,
        user_id: selectedUser.user_id,
        amount: parseFloat(amount).toFixed(2),
        currency: currency,
        occurred_at: new Date().toISOString(),
      }
      setJsonPayload(JSON.stringify(payload, null, 2))
    } else {
      setJsonPayload("")
    }
  }, [selectedUser, amount, currency, providerEventId, iban])

  const fetchUsers = async () => {
    setUsersLoading(true)
    setUsersError("")
    try {
      const data = await adminApi.listUsers({ limit: 200 })
      setUsers(data)
    } catch (err: any) {
      const apiError = parseApiError(err)
      const errorMsg = apiError.message || "Failed to load users"
      setUsersError(`${errorMsg}${apiError.code ? ` (${apiError.code})` : ''}${apiError.trace_id ? ` - Trace ID: ${apiError.trace_id}` : ''}`)
      console.error('[ZAND Webhook] Failed to fetch users:', {
        error: apiError,
        status: apiError.status,
        code: apiError.code,
        trace_id: apiError.trace_id,
        endpoint: 'admin/v1/users',
      })
    } finally {
      setUsersLoading(false)
    }
  }

  // Filter users by search
  const filteredUsers = userSearch
    ? users.filter(
        (u) =>
          u.email.toLowerCase().includes(userSearch.toLowerCase()) ||
          (u.first_name && u.first_name.toLowerCase().includes(userSearch.toLowerCase())) ||
          (u.last_name && u.last_name.toLowerCase().includes(userSearch.toLowerCase()))
      )
    : users

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setResponse("")
    setError(null)
    setSuccess(false)

    if (!selectedUser) {
      setError({ message: "Please select a user" })
      setLoading(false)
      return
    }

    try {
      const payload = {
        provider_event_id: providerEventId || `ZAND-EVT-${Date.now()}`,
        iban: iban,
        user_id: selectedUser.user_id,
        amount: parseFloat(amount).toFixed(2),
        currency: currency,
        occurred_at: new Date().toISOString(),
      }

      const url = getApiUrl('webhooks/v1/zand/deposit')
      
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      const data = await response.json()
      
      if (!response.ok) {
        const errorData = parseApiError({
          message: data.detail || data.message || `HTTP ${response.status}`,
          code: data.code || `HTTP_${response.status}`,
          trace_id: data.trace_id || response.headers.get('X-Trace-ID'),
        })
        setError(errorData)
        setResponse(JSON.stringify(data, null, 2))
      } else {
        setSuccess(true)
        setResponse(JSON.stringify(data, null, 2))
        // Clear form after success
        setTimeout(() => {
          setSelectedUser(null)
          setAmount("1000.00")
          setUserSearch("")
        }, 2000)
      }
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError)
      setResponse(`Error: ${apiError.message}`)
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    // Simple feedback (could be improved with toast)
    alert("Copied to clipboard!")
  }

  return (
    <main className="container mx-auto p-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">ZAND Webhook Simulator</h1>
      
      <div className="bg-blue-50 border border-blue-200 rounded p-4 mb-6">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> This tool simulates ZAND bank deposit webhooks. 
          The webhook endpoint does not require authentication, but the payload must be valid JSON 
          matching the ZAND webhook format.
        </p>
      </div>

      {/* Success message */}
      {success && (
        <div className="bg-green-100 text-green-700 p-3 rounded mb-4">
          <div className="font-semibold">✅ Webhook sent successfully!</div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
          <div className="font-semibold">Error: {error.message}</div>
          {error.code && <div className="text-sm mt-1">Code: {error.code}</div>}
          {error.trace_id && (
            <div className="text-xs font-mono mt-1">Trace ID: {error.trace_id}</div>
          )}
        </div>
      )}

      {/* Users loading error */}
      {usersError && (
        <div className="bg-yellow-100 text-yellow-700 p-3 rounded mb-4">
          <div className="font-semibold">Warning: {usersError}</div>
          <div className="text-sm mt-2">
            <p>Possible causes:</p>
            <ul className="list-disc list-inside ml-2 mt-1">
              <li>Not logged in or session expired - <a href="/login" className="underline">Login here</a></li>
              <li>Backend not running on http://localhost:8000</li>
              <li>Missing ADMIN role permissions</li>
            </ul>
          </div>
          <button
            onClick={fetchUsers}
            className="text-sm underline mt-2"
          >
            Retry
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* User Selection */}
        <div>
          <label className="block mb-2 font-medium">User *</label>
          {usersLoading ? (
            <div className="text-gray-500">Loading users...</div>
          ) : usersError ? (
            <div className="p-4 border rounded bg-gray-50">
              <div className="text-sm text-gray-600 mb-2">
                Cannot load users list. You can still enter a user_id manually in the Advanced JSON section.
              </div>
              <div className="text-xs text-gray-500">
                Or <a href="/login" className="text-blue-600 underline">login</a> and retry.
              </div>
            </div>
          ) : (
            <>
              <input
                type="text"
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
                placeholder="Search by email or name..."
                className="w-full p-2 border rounded mb-2"
              />
              <div className="border rounded max-h-48 overflow-y-auto">
                {filteredUsers.length === 0 ? (
                  <div className="p-4 text-gray-500 text-center">
                    {userSearch ? "No users found matching your search" : "No users found"}
                  </div>
                ) : (
                  filteredUsers.map((user) => (
                    <div
                      key={user.user_id}
                      onClick={() => {
                        setSelectedUser(user)
                        setUserSearch(user.email)
                      }}
                      className={`p-3 cursor-pointer hover:bg-gray-50 border-b ${
                        selectedUser?.user_id === user.user_id
                          ? "bg-blue-50 border-blue-200"
                          : ""
                      }`}
                    >
                      <div className="font-medium">{user.email}</div>
                      {(user.first_name || user.last_name) && (
                        <div className="text-sm text-gray-600">
                          {user.first_name} {user.last_name}
                        </div>
                      )}
                      <div className="text-xs text-gray-500">ID: {user.user_id.substring(0, 8)}...</div>
                    </div>
                  ))
                )}
              </div>
              {selectedUser && (
                <div className="mt-2 text-sm text-green-600">
                  ✓ Selected: {selectedUser.email}
                </div>
              )}
            </>
          )}
        </div>

        {/* Amount and Currency */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block mb-2 font-medium">Amount (AED) *</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              min="0.01"
              step="0.01"
              required
              className="w-full p-2 border rounded"
            />
          </div>
          <div>
            <label className="block mb-2 font-medium">Currency</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full p-2 border rounded"
            >
              <option value="AED">AED</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
        </div>

        {/* IBAN */}
        <div>
          <label className="block mb-2 font-medium">IBAN</label>
          <input
            type="text"
            value={iban}
            onChange={(e) => setIban(e.target.value)}
            placeholder="AE123456789012345678901"
            className="w-full p-2 border rounded"
          />
        </div>

        {/* Provider Event ID */}
        <div>
          <label className="block mb-2 font-medium">Provider Event ID (auto-generated if empty)</label>
          <input
            type="text"
            value={providerEventId}
            onChange={(e) => setProviderEventId(e.target.value)}
            placeholder="ZAND-EVT-..."
            className="w-full p-2 border rounded font-mono text-sm"
          />
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || !selectedUser}
          className="w-full bg-blue-600 text-white px-4 py-3 rounded disabled:opacity-50 hover:bg-blue-700 font-medium"
        >
          {loading ? "Sending..." : "Send Webhook"}
        </button>

        {/* Advanced JSON Section */}
        <div className="border rounded">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full p-3 text-left font-medium bg-gray-50 hover:bg-gray-100 flex items-center justify-between"
          >
            <span>Advanced: JSON Payload</span>
            <span>{showAdvanced ? "▼" : "▶"}</span>
          </button>
          {showAdvanced && (
            <div className="p-4">
              {jsonPayload ? (
                <>
                  <div className="flex justify-end mb-2">
                    <button
                      type="button"
                      onClick={() => copyToClipboard(jsonPayload)}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Copy JSON
                    </button>
                  </div>
                  <pre className="bg-gray-100 p-4 rounded overflow-auto text-sm font-mono">
                    {jsonPayload}
                  </pre>
                </>
              ) : (
                <div className="text-gray-500 text-sm">
                  Select a user to see the generated JSON payload
                </div>
              )}
            </div>
          )}
        </div>
      </form>
      
      {/* Response */}
      {response && (
        <div className="mt-6 border rounded">
          <div className="p-3 bg-gray-50 border-b flex items-center justify-between">
            <h2 className="font-bold">Response:</h2>
            <button
              type="button"
              onClick={() => copyToClipboard(response)}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Copy Response
            </button>
          </div>
          <pre className="p-4 overflow-auto text-sm font-mono bg-gray-50">
            {response}
          </pre>
        </div>
      )}
    </main>
  )
}
