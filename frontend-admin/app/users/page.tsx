"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { apiRequest, parseApiError, getToken } from "@/lib/api"

interface User {
  user_id: string
  email: string
  first_name?: string
  last_name?: string
  status: string
  created_at: string
}

interface ResolveUserResponse {
  user_id: string
  email: string
  found: boolean
}

export default function UsersPage() {
  const router = useRouter()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchResult, setSearchResult] = useState<ResolveUserResponse | null>(null)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      router.push("/login")
      return
    }

    fetchUsers()
  }, [router])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      setError("")
      const data = await apiRequest<User[]>('admin/v1/users?limit=100')
      setUsers(data)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message)
      if (apiError.status === 401 || apiError.status === 403) {
        router.push("/login")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return

    try {
      setSearchLoading(true)
      setSearchResult(null)
      setError("")
      
      const result = await apiRequest<ResolveUserResponse>('admin/v1/users/resolve', {
        method: 'POST',
        body: JSON.stringify({
          email: searchQuery.trim(),
        }),
      })
      
      setSearchResult(result)
      if (result.found) {
        // Navigate to user detail page
        router.push(`/users/${result.user_id}`)
      }
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message)
    } finally {
      setSearchLoading(false)
    }
  }

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Users</h1>
        <p>Loading users...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Users</h1>
      
      {error && (
        <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
          <div className="font-semibold">Error: {error}</div>
        </div>
      )}

      {/* Search User by Email */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <h2 className="text-lg font-semibold mb-3">Search User by Email</h2>
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="email"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Enter email address"
            className="flex-1 p-2 border rounded"
          />
          <button
            type="submit"
            disabled={searchLoading || !searchQuery.trim()}
            className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
          >
            {searchLoading ? "Searching..." : "Search"}
          </button>
        </form>
        {searchResult && (
          <div className="mt-2 text-sm">
            {searchResult.found ? (
              <span className="text-green-600">Found: {searchResult.email}</span>
            ) : (
              <span className="text-gray-600">User not found</span>
            )}
          </div>
        )}
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">All Users ({users.length})</h2>
        </div>
        {users.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No users found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {users.map((user) => (
                  <tr
                    key={user.user_id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => router.push(`/users/${user.user_id}`)}
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {user.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {user.first_name} {user.last_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span
                        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          user.status === "ACTIVE"
                            ? "bg-green-100 text-green-800"
                            : user.status === "SUSPENDED"
                            ? "bg-red-100 text-red-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {user.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(user.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600">
                      <Link
                        href={`/users/${user.user_id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="hover:underline"
                      >
                        View →
                      </Link>
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
