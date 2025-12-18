"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { getToken, getApiUrl } from "@/lib/api"

interface UserInfo {
  user_id: string
  email: string
  first_name?: string
  last_name?: string
  status: string
}

export default function MePage() {
  const router = useRouter()
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchUserInfo = async () => {
      const token = getToken()
      if (!token) {
        router.push("/login")
        return
      }

      try {
        const url = getApiUrl('api/v1/me')
        
        // DEV: Debug logging
        if (process.env.NODE_ENV === 'development') {
          console.log('[ME DEBUG]', {
            url,
            tokenPreview: token.substring(0, 20) + '...',
          })
        }

        const response = await fetch(url, {
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        })

        // DEV: Debug response
        if (process.env.NODE_ENV === 'development') {
          console.log('[ME DEBUG]', {
            status: response.status,
            statusText: response.statusText,
          })
        }

        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error?.message || data.detail || "Failed to fetch user info")
        }

        const data = await response.json()
        
        // DEV: Debug response data
        if (process.env.NODE_ENV === 'development') {
          console.log('[ME DEBUG]', {
            responseData: data,
          })
        }

        setUserInfo(data)
      } catch (err: any) {
        setError(err.message || "Failed to load user info")
      } finally {
        setLoading(false)
      }
    }

    fetchUserInfo()
  }, [router])

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-4">My Profile</h1>
        <p>Loading...</p>
      </main>
    )
  }

  if (error) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-4">My Profile</h1>
        <div className="bg-red-100 text-red-700 p-3 rounded">{error}</div>
        <a href="/" className="text-blue-600 hover:underline mt-4 inline-block">← Back to home</a>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">My Profile</h1>
        <a href="/" className="text-blue-600 hover:underline">← Back to home</a>
      </div>

      {userInfo && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 max-w-2xl">
          <h2 className="text-xl font-semibold mb-4">User Information</h2>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500">User ID</dt>
              <dd className="mt-1 text-sm text-gray-900 font-mono">{userInfo.user_id}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Email</dt>
              <dd className="mt-1 text-sm text-gray-900">{userInfo.email}</dd>
            </div>
            {userInfo.first_name && (
              <div>
                <dt className="text-sm font-medium text-gray-500">First Name</dt>
                <dd className="mt-1 text-sm text-gray-900">{userInfo.first_name}</dd>
              </div>
            )}
            {userInfo.last_name && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Last Name</dt>
                <dd className="mt-1 text-sm text-gray-900">{userInfo.last_name}</dd>
              </div>
            )}
            <div>
              <dt className="text-sm font-medium text-gray-500">Status</dt>
              <dd className="mt-1">
                <span className={`px-2 py-1 rounded text-sm ${
                  userInfo.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {userInfo.status}
                </span>
              </dd>
            </div>
          </dl>
        </div>
      )}
    </main>
  )
}

