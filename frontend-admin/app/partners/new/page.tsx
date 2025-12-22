"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { partnersAdminApi, parseApiError, type CreatePartnerPayload } from "@/lib/api"

export default function NewPartnerPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState<CreatePartnerPayload>({
    code: "",
    legal_name: "",
    trade_name: "",
    description_markdown: "",
    website_url: "",
    address_line1: "",
    address_line2: "",
    city: "",
    country: "",
    contact_email: "",
    contact_phone: "",
    ceo_name: "",
    ceo_title: "",
    ceo_quote: "",
    ceo_bio_markdown: "",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const partner = await partnersAdminApi.createPartner(formData)
      router.push(`/partners/${partner.id}`)
    } catch (err: any) {
      const apiError = parseApiError(err)
      let errorMessage = apiError.message || "Failed to create partner"
      
      // Handle specific error codes with user-friendly messages
      if (apiError.code === "HTTP_409" || apiError.code === "PARTNER_CODE_EXISTS" || apiError.message?.includes("PARTNER_CODE_EXISTS")) {
        errorMessage = `A partner with code "${formData.code}" already exists. Please use a different code.`
      } else if (apiError.code && apiError.code !== "HTTP_409") {
        errorMessage = `${apiError.code}: ${errorMessage}`
      }
      
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="container mx-auto p-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">Create New Partner</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded mb-4">
          <p>{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-sm space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Code *</label>
            <input
              type="text"
              required
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="unique-partner-code"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Legal Name *</label>
            <input
              type="text"
              required
              value={formData.legal_name}
              onChange={(e) => setFormData({ ...formData, legal_name: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Trade Name</label>
          <input
            type="text"
            value={formData.trade_name}
            onChange={(e) => setFormData({ ...formData, trade_name: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {loading ? "Creating..." : "Create Partner"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="bg-gray-200 text-gray-800 px-6 py-2 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </main>
  )
}

