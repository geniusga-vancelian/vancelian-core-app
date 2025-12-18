'use client'

import { useState, useEffect } from 'react'

interface JWTClaims {
  sub?: string
  email?: string
  roles?: string[]
  [key: string]: any
}

export function TokenBar() {
  const [token, setToken] = useState<string>('')
  const [claims, setClaims] = useState<JWTClaims | null>(null)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    // Load token from sessionStorage on mount
    const storedToken = sessionStorage.getItem('dev_jwt_token')
    if (storedToken) {
      setToken(storedToken)
      decodeToken(storedToken)
    }
  }, [])

  const decodeToken = (jwt: string) => {
    try {
      setError('')
      // JWT format: header.payload.signature
      const parts = jwt.split('.')
      if (parts.length !== 3) {
        throw new Error('Invalid JWT format')
      }
      
      // Decode payload (base64url) - use atob for browser
      const payload = parts[1]
      const decodedPayload = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
      const decoded = JSON.parse(decodedPayload)
      
      setClaims(decoded)
    } catch (err: any) {
      setError(err.message || 'Failed to decode token')
      setClaims(null)
    }
  }

  const handleTokenChange = (newToken: string) => {
    setToken(newToken)
    if (newToken.trim()) {
      sessionStorage.setItem('dev_jwt_token', newToken)
      decodeToken(newToken)
    } else {
      sessionStorage.removeItem('dev_jwt_token')
      setClaims(null)
      setError('')
    }
  }

  const handleClear = () => {
    setToken('')
    sessionStorage.removeItem('dev_jwt_token')
    setClaims(null)
    setError('')
  }

  return (
    <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-3">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              JWT Token (DEV-ONLY - No verification):
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={token}
                onChange={(e) => handleTokenChange(e.target.value)}
                placeholder="Paste JWT token here..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-xs font-mono"
              />
              {token && (
                <button
                  onClick={handleClear}
                  className="px-3 py-2 bg-gray-200 hover:bg-gray-300 rounded-md text-sm"
                >
                  Clear
                </button>
              )}
            </div>
            {error && (
              <p className="mt-1 text-xs text-red-600">{error}</p>
            )}
          </div>
          {claims && (
            <div className="bg-white border border-gray-200 rounded-md p-3 min-w-[300px]">
              <div className="text-xs font-semibold text-gray-700 mb-2">Token Claims:</div>
              <div className="text-xs space-y-1">
                {claims.sub && (
                  <div><span className="font-medium">sub:</span> {claims.sub}</div>
                )}
                {claims.email && (
                  <div><span className="font-medium">email:</span> {claims.email}</div>
                )}
                {claims.roles && (
                  <div>
                    <span className="font-medium">roles:</span>{' '}
                    {Array.isArray(claims.roles) ? claims.roles.join(', ') : claims.roles}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

