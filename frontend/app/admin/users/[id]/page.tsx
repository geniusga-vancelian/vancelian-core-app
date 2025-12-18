'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { adminApi, ApiError } from '@/lib/api'

interface UserDetail {
  user_id: string
  email: string
  first_name?: string
  last_name?: string
  phone?: string
  status: string
  external_subject?: string
  created_at: string
}

export default function UserDetailPage() {
  const params = useParams()
  const router = useRouter()
  const userId = params.id as string
  const [user, setUser] = useState<UserDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    if (userId) {
      fetchUser()
    }
  }, [userId])

  const fetchUser = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await adminApi.getUser(userId)
      setUser(data)
    } catch (err: any) {
      const apiError = err as ApiError
      setError(apiError)
      if (apiError.code === 'HTTP_401' || apiError.code === 'HTTP_403') {
        router.push('/login')
      }
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto p-8">
        <Link href="/admin/users" className="text-indigo-600 mb-4 inline-block">← Back to Users</Link>
        <h1 className="text-3xl font-bold mb-6">User Details</h1>
        <p>Loading user details...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto p-8">
        <Link href="/admin/users" className="text-indigo-600 mb-4 inline-block">← Back to Users</Link>
        <h1 className="text-3xl font-bold mb-6">User Details</h1>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          <p className="font-semibold">Error: {error.message}</p>
          {error.code && <p className="text-sm">Code: {error.code}</p>}
          {error.trace_id && (
            <p className="text-xs font-mono mt-1">Trace ID: {error.trace_id}</p>
          )}
        </div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="max-w-7xl mx-auto p-8">
        <Link href="/admin/users" className="text-indigo-600 mb-4 inline-block">← Back to Users</Link>
        <h1 className="text-3xl font-bold mb-6">User Details</h1>
        <p>User not found</p>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto p-8">
      <Link href="/admin/users" className="text-indigo-600 mb-4 inline-block">← Back to Users</Link>
      <h1 className="text-3xl font-bold mb-6">User Details</h1>
      
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">User Information</h2>
        </div>
        <div className="px-6 py-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">User ID</label>
              <p className="text-sm text-gray-900 font-mono">{user.user_id}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">Email</label>
              <p className="text-sm text-gray-900">{user.email}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">First Name</label>
              <p className="text-sm text-gray-900">{user.first_name || 'N/A'}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">Last Name</label>
              <p className="text-sm text-gray-900">{user.last_name || 'N/A'}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">Phone</label>
              <p className="text-sm text-gray-900">{user.phone || 'N/A'}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">Status</label>
              <span
                className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                  user.status === 'ACTIVE'
                    ? 'bg-green-100 text-green-800'
                    : user.status === 'SUSPENDED'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {user.status}
              </span>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">External Subject</label>
              <p className="text-sm text-gray-900 font-mono">{user.external_subject || 'N/A'}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">Created At</label>
              <p className="text-sm text-gray-900">{new Date(user.created_at).toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

