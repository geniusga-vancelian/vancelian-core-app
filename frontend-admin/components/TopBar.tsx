"use client"

import { useRouter, usePathname } from "next/navigation"
import Link from "next/link"
import { useState, useEffect } from "react"

export function TopBar() {
  const router = useRouter()
  const pathname = usePathname()
  const [token, setToken] = useState<string | null>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    if (typeof window !== "undefined") {
      setToken(localStorage.getItem("access_token"))
      setMounted(true)
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem("access_token")
    localStorage.removeItem("user_id")
    router.push("/login")
  }

  // Don't show on login page
  if (pathname === "/login") {
    return null
  }

  // Render minimal version during SSR
  if (!mounted) {
    return (
      <nav className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-8 py-4 flex justify-between items-center">
          <Link href="/" className="text-lg font-semibold text-gray-900">
            Vancelian Admin
          </Link>
        </div>
      </nav>
    )
  }

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="container mx-auto px-8 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-6">
          <Link href="/" className="text-lg font-semibold text-gray-900">
            Vancelian Admin
          </Link>
          {token && (
            <div className="flex space-x-4">
              <Link
                href="/users"
                className={`text-gray-600 hover:text-gray-900 ${
                  pathname?.startsWith("/users") ? "font-semibold text-blue-600" : ""
                }`}
              >
                Users
              </Link>
              <Link
                href="/compliance"
                className={`text-gray-600 hover:text-gray-900 ${
                  pathname === "/compliance" ? "font-semibold text-blue-600" : ""
                }`}
              >
                Compliance
              </Link>
              <Link
                href="/tools/zand-webhook"
                className={`text-gray-600 hover:text-gray-900 ${
                  pathname === "/tools/zand-webhook" ? "font-semibold text-blue-600" : ""
                }`}
              >
                ZAND Webhook
              </Link>
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

