"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import Link from "next/link"
import { offersAdminApi, parseApiError, type Offer, type UpdateOfferPayload } from "@/lib/api"

export default function OfferDetailPage() {
  const router = useRouter()
  const params = useParams()
  const offerId = params.id as string
  
  const [offer, setOffer] = useState<Offer | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState<UpdateOfferPayload>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (offerId) {
      loadOffer()
    }
  }, [offerId])

  const loadOffer = async () => {
    setLoading(true)
    setError(null)
    setTraceId(null)
    
    try {
      const data = await offersAdminApi.getOffer(offerId)
      setOffer(data)
      setEditForm({
        name: data.name,
        description: data.description || "",
        max_amount: data.max_amount,
        maturity_date: data.maturity_date || undefined,
      })
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to load offer")
      setTraceId(apiError.trace_id || null)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setTraceId(null)

    try {
      const updated = await offersAdminApi.updateOffer(offerId, editForm)
      setOffer(updated)
      setEditing(false)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to update offer")
      setTraceId(apiError.trace_id || null)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusAction = async (action: 'publish' | 'pause' | 'close') => {
    try {
      let updated: Offer
      if (action === 'publish') {
        updated = await offersAdminApi.publishOffer(offerId)
      } else if (action === 'pause') {
        updated = await offersAdminApi.pauseOffer(offerId)
      } else {
        updated = await offersAdminApi.closeOffer(offerId)
      }
      setOffer(updated)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || `Failed to ${action} offer`)
      setTraceId(apiError.trace_id || null)
    }
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      DRAFT: "bg-gray-100 text-gray-800",
      LIVE: "bg-green-100 text-green-800",
      PAUSED: "bg-yellow-100 text-yellow-800",
      CLOSED: "bg-red-100 text-red-800",
    }
    return colors[status as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  if (loading) {
    return (
      <main className="container mx-auto p-8">
        <p>Loading...</p>
      </main>
    )
  }

  if (!offer) {
    return (
      <main className="container mx-auto p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Offer not found</p>
        </div>
        <Link href="/offers" className="text-blue-600 hover:underline mt-4 inline-block">
          ← Back to Offers
        </Link>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8">
      <div className="mb-6">
        <Link href="/offers" className="text-blue-600 hover:underline">
          ← Back to Offers
        </Link>
      </div>

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">{offer.name}</h1>
        <div className="flex gap-2">
          {offer.status === 'DRAFT' && (
            <button
              onClick={() => handleStatusAction('publish')}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
            >
              Publish
            </button>
          )}
          {offer.status === 'LIVE' && (
            <>
              <button
                onClick={() => handleStatusAction('pause')}
                className="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700"
              >
                Pause
              </button>
              <button
                onClick={() => handleStatusAction('close')}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
              >
                Close
              </button>
            </>
          )}
          {offer.status === 'PAUSED' && (
            <>
              <button
                onClick={() => handleStatusAction('publish')}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Resume
              </button>
              <button
                onClick={() => handleStatusAction('close')}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
              >
                Close
              </button>
            </>
          )}
          <button
            onClick={() => setEditing(!editing)}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            {editing ? "Cancel Edit" : "Edit"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800">{error}</div>
          {traceId && (
            <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
          )}
        </div>
      )}

      {/* Offer Details Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        {editing ? (
          <form onSubmit={handleUpdate}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input
                  type="text"
                  value={editForm.name || ""}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={editForm.description || ""}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows={4}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Amount</label>
                <input
                  type="number"
                  step="0.01"
                  value={editForm.max_amount || ""}
                  onChange={(e) => setEditForm({ ...editForm, max_amount: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Maturity Date</label>
                <input
                  type="datetime-local"
                  value={editForm.maturity_date ? new Date(editForm.maturity_date).toISOString().slice(0, 16) : ""}
                  onChange={(e) => setEditForm({ ...editForm, maturity_date: e.target.value || undefined })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditing(false)
                    setEditForm({
                      name: offer.name,
                      description: offer.description || "",
                      max_amount: offer.max_amount,
                      maturity_date: offer.maturity_date || undefined,
                    })
                  }}
                  className="bg-gray-200 text-gray-800 px-4 py-2 rounded hover:bg-gray-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Code</label>
                <p className="text-lg font-mono">{offer.code}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Status</label>
                <p>
                  <span className={`px-2 py-1 rounded text-sm ${getStatusBadge(offer.status)}`}>
                    {offer.status}
                  </span>
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Currency</label>
                <p className="text-lg">{offer.currency}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Max Amount</label>
                <p className="text-lg font-mono">
                  {parseFloat(offer.max_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Committed Amount</label>
                <p className="text-lg font-mono">
                  {parseFloat(offer.committed_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Remaining Amount</label>
                <p className="text-lg font-mono text-green-600">
                  {parseFloat(offer.remaining_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {offer.currency}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Maturity Date</label>
                <p className="text-lg">
                  {offer.maturity_date ? new Date(offer.maturity_date).toLocaleString() : "-"}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Created At</label>
                <p className="text-lg">
                  {new Date(offer.created_at).toLocaleString()}
                </p>
              </div>
            </div>
            {offer.description && (
              <div>
                <label className="text-sm font-medium text-gray-500">Description</label>
                <p className="mt-1 text-gray-700">{offer.description}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Investments List - TODO: Backend endpoint needed */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Investments</h2>
        <div className="text-gray-500 text-sm">
          <p>TODO: Backend endpoint to list investments by offer_id is not yet implemented.</p>
          <p className="mt-2">When available, this section will show:</p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>User email</li>
            <li>Requested amount</li>
            <li>Accepted amount</li>
            <li>Status</li>
            <li>Created at</li>
          </ul>
        </div>
      </div>
    </main>
  )
}
