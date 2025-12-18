"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { getApiUrl, setToken } from "@/lib/api"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<{
    message?: string
    code?: string
    status?: number
    trace_id?: string
  } | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const baseUrl = getApiUrl('api/v1/auth/login')
      // Trim email and password to avoid whitespace issues
      const trimmedEmail = email.trim()
      const trimmedPassword = password.trim()
      const requestBody = { email: trimmedEmail, password: trimmedPassword }

      // DEV: Debug logging
      if (process.env.NODE_ENV === 'development') {
        console.log('[LOGIN DEBUG]', {
          baseUrl,
          requestUrl: baseUrl,
          requestBody: { email: trimmedEmail, password: '***', passwordLength: trimmedPassword.length },
          originalEmail: email,
          originalPasswordLength: password.length,
        })
      }

      const response = await fetch(baseUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      })

      // DEV: Debug response
      if (process.env.NODE_ENV === 'development') {
        console.log('[LOGIN DEBUG]', {
          status: response.status,
          statusText: response.statusText,
          headers: Object.fromEntries(response.headers.entries()),
        })
      }

      const data = await response.json()

      // DEV: Debug response data
      if (process.env.NODE_ENV === 'development') {
        console.log('[LOGIN DEBUG]', {
          responseData: data,
        })
      }

      if (!response.ok) {
        // Extract error details from response
        const errorData = data.error || data
        throw {
          message: errorData.message || errorData.detail || "Login failed",
          code: errorData.code,
          status: response.status,
          trace_id: errorData.trace_id,
        }
      }

      // Store token in sessionStorage
      if (data.access_token) {
        setToken(data.access_token)
        
        // DEV: Verify token storage
        if (process.env.NODE_ENV === 'development') {
          console.log('[LOGIN DEBUG]', {
            tokenStored: !!sessionStorage.getItem('dev_client_token'),
            tokenPreview: data.access_token.substring(0, 20) + '...',
          })
        }
      }
      
      // Redirect to home
      router.push("/")
    } catch (err: any) {
      // Handle error object or Error instance
      if (typeof err === 'object' && err !== null && 'message' in err) {
        setError(err)
      } else {
        setError({ message: err?.message || "Login failed" })
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="container mx-auto p-8 max-w-md">
      <h1 className="text-3xl font-bold mb-6">Login</h1>
      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
          <div className="font-semibold">{error.message || "Login failed"}</div>
          {error.code && <div className="text-sm mt-1">Code: {error.code}</div>}
          {error.status && <div className="text-sm">Status: {error.status}</div>}
          {error.trace_id && (
            <div className="text-xs mt-1 text-red-600 font-mono">
              Trace ID: {error.trace_id}
            </div>
          )}
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
      <p className="mt-4 text-center">
        Don't have an account? <a href="/register" className="text-blue-600">Register</a>
      </p>
    </main>
  )
}

