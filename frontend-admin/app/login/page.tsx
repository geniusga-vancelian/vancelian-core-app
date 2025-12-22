"use client"

/**
 * Admin Login Page
 */

import { useState } from "react"
import { useRouter } from "next/navigation"
import { getApiUrl, getApiBaseUrl } from "@/lib/config"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      // Use centralized config
      const apiBaseUrl = getApiBaseUrl()
      // Trim email and password to avoid whitespace issues
      const trimmedEmail = email.trim()
      const trimmedPassword = password.trim()
      const requestBody = { email: trimmedEmail, password: trimmedPassword }
      const requestUrl = getApiUrl('api/v1/auth/login')

      // DEV: Debug logging
      if (process.env.NODE_ENV === 'development') {
        console.log('[ADMIN LOGIN DEBUG]', {
          apiBaseUrl,
          requestUrl,
          requestBody: { email: trimmedEmail, password: '***', passwordLength: trimmedPassword.length },
        })
      }

      const response = await fetch(requestUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      })

      // DEV: Debug response
      if (process.env.NODE_ENV === 'development') {
        console.log('[ADMIN LOGIN DEBUG]', {
          status: response.status,
          statusText: response.statusText,
          ok: response.ok,
          contentType: response.headers.get('content-type'),
        })
      }

      // Parse response - handle both success and error cases
      let data
      try {
        const text = await response.text()
        if (process.env.NODE_ENV === 'development') {
          console.log('[ADMIN LOGIN DEBUG]', {
            responseText: text.substring(0, 200),
          })
        }
        data = JSON.parse(text)
      } catch (parseError) {
        throw new Error(`Failed to parse server response: ${parseError}`)
      }

      // DEV: Debug response data
      if (process.env.NODE_ENV === 'development') {
        console.log('[ADMIN LOGIN DEBUG]', {
          hasAccessToken: !!data.access_token,
          hasError: !!data.error,
          errorData: data.error || null,
          fullResponse: data,
        })
      }

      if (!response.ok) {
        // Extract error details
        const errorData = data.error || data
        const errorMessage = errorData.message || errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        const errorCode = errorData.code
        const traceId = errorData.trace_id
        
        let fullError = errorMessage
        if (errorCode) fullError += ` (Code: ${errorCode})`
        if (traceId) fullError += ` [Trace: ${traceId}]`
        
        throw new Error(fullError)
      }

      if (!data.access_token) {
        throw new Error("No access token received from server")
      }

      localStorage.setItem("access_token", data.access_token)
      localStorage.setItem("user_id", data.user_id)
      
      // DEV: Verify token storage
      if (process.env.NODE_ENV === 'development') {
        console.log('[ADMIN LOGIN DEBUG]', {
          tokenStored: !!localStorage.getItem('access_token'),
          tokenPreview: data.access_token.substring(0, 20) + '...',
        })
      }
      
      router.push("/users")
    } catch (err: any) {
      setError(err.message || "Login failed")
      if (process.env.NODE_ENV === 'development') {
        console.error('[ADMIN LOGIN ERROR]', err)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="container mx-auto p-8 max-w-md">
      <h1 className="text-3xl font-bold mb-6">Admin Login</h1>
      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
          <div className="font-semibold">{error}</div>
          <div className="text-sm mt-1">Check browser console (F12) for details</div>
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full p-2 border rounded"
          />
        </div>
        <div>
          <label className="block mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full p-2 border rounded"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white p-2 rounded disabled:opacity-50"
        >
          {loading ? "Logging in..." : "Login"}
        </button>
      </form>
    </main>
  )
}

