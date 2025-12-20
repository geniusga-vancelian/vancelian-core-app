"use client"

import { useRouter, usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { getToken, removeToken } from "@/lib/api"

export function TopBar() {
  const router = useRouter()
  const pathname = usePathname()
  const [token, setToken] = useState<string | null>(null)
  const [mounted, setMounted] = useState(false)

  // Only check token on client side after mount
  useEffect(() => {
    setMounted(true)
    setToken(getToken())
  }, [])

  const handleLogout = () => {
    removeToken()
    setToken(null)
    router.push("/login")
  }

  // Don't show on login/register pages
  if (pathname === "/login" || pathname === "/register") {
    return null
  }

  // During SSR or before mount, render minimal version
  if (!mounted) {
    return (
      <nav className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-8 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-6">
            <a href="/" className="text-lg font-semibold text-gray-900">
              Vancelian Client
            </a>
          </div>
        </div>
      </nav>
    )
  }

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="container mx-auto px-8 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-6">
          <a href="/" className="text-lg font-semibold text-gray-900">
            Vancelian Client
          </a>
          {token && (
            <div className="flex space-x-4">
              <a href="/offers" className="text-gray-600 hover:text-gray-900">Offers</a>
              <a href="/blog" className="text-gray-600 hover:text-gray-900">Blog</a>
              <a href="/" className="text-gray-600 hover:text-gray-900">Dashboard</a>
              <a href="/transactions" className="text-gray-600 hover:text-gray-900">Transactions</a>
              <a href="/me" className="text-gray-600 hover:text-gray-900">Profile</a>
            </div>
          )}
        </div>
        {token && (
          <button
            onClick={handleLogout}
            className="text-gray-600 hover:text-gray-900"
          >
            Logout
          </button>
        )}
      </div>
    </nav>
  )
}

