"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter, useParams } from "next/navigation"
import Link from "next/link"
import { partnersAdminApi, offersAdminApi, systemApi, parseApiError, type Partner, type UpdatePartnerPayload, type Offer } from "@/lib/api"
import { MarkdownProse } from "@/components/MarkdownProse"

type Tab = 'overview' | 'ceo' | 'offers' | 'team' | 'media' | 'documents' | 'portfolio'

export default function PartnerDetailPage() {
  const router = useRouter()
  const params = useParams()
  const partnerId = params.id as string
  
  const [partner, setPartner] = useState<Partner | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState<UpdatePartnerPayload>({})
  const [saving, setSaving] = useState(false)

  // CEO module state
  const [ceoEditing, setCeoEditing] = useState(false)
  const [ceoForm, setCeoForm] = useState({
    ceo_name: "",
    ceo_title: "",
    ceo_quote: "",
    ceo_bio_markdown: "",
    ceo_photo_media_id: null as string | null,
  })

  // Offers linking state
  const [availableOffers, setAvailableOffers] = useState<Offer[]>([])
  const [primaryOfferId, setPrimaryOfferId] = useState<string | null>(null)
  const [additionalOfferIds, setAdditionalOfferIds] = useState<string[]>([])
  const [offerSearchQuery, setOfferSearchQuery] = useState<string>("")
  const [savingOffers, setSavingOffers] = useState(false)

  // Media & Documents state
  const [uploadingMedia, setUploadingMedia] = useState(false)
  const [uploadingDocument, setUploadingDocument] = useState(false)
  const imageFileInputRef = useRef<HTMLInputElement>(null)
  const videoFileInputRef = useRef<HTMLInputElement>(null)
  const documentFileInputRef = useRef<HTMLInputElement>(null)

  // Team members state
  const [teamEditing, setTeamEditing] = useState(false)
  const [teamMembers, setTeamMembers] = useState(partner?.team_members || [])

  // Portfolio state
  const [portfolioProjects, setPortfolioProjects] = useState(partner?.portfolio_projects || [])

  useEffect(() => {
    if (partnerId) {
      loadPartner()
      loadAvailableOffers()
    }
  }, [partnerId])

  useEffect(() => {
    if (partner) {
      setTeamMembers(partner.team_members)
      setPortfolioProjects(partner.portfolio_projects)
      // Initialize offers
      const primary = partner.linked_offers.find(o => o.is_primary)
      setPrimaryOfferId(primary?.id || null)
      setAdditionalOfferIds(partner.linked_offers.filter(o => !o.is_primary).map(o => o.id))
    }
  }, [partner])

  const loadPartner = async () => {
    setLoading(true)
    setError(null)
    setTraceId(null)
    
    try {
      const data = await partnersAdminApi.getPartner(partnerId)
      setPartner(data)
      setEditForm({
        code: data.code,
        legal_name: data.legal_name,
        trade_name: data.trade_name || "",
        description_markdown: data.description_markdown || "",
        website_url: data.website_url || "",
        address_line1: data.address_line1 || "",
        address_line2: data.address_line2 || "",
        city: data.city || "",
        country: data.country || "",
        contact_email: data.contact_email || "",
        contact_phone: data.contact_phone || "",
        status: data.status as any,
      })
      setCeoForm({
        ceo_name: data.ceo_name || "",
        ceo_title: data.ceo_title || "",
        ceo_quote: data.ceo_quote || "",
        ceo_bio_markdown: data.ceo_bio_markdown || "",
        ceo_photo_media_id: data.ceo_photo_media_id || null,
      })
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || "Failed to load partner")
      setTraceId(apiError.trace_id || null)
    } finally {
      setLoading(false)
    }
  }

  const loadAvailableOffers = async () => {
    try {
      const offers = await offersAdminApi.listOffers({ limit: 100 })
      setAvailableOffers(offers)
    } catch (err) {
      console.error('Failed to load offers:', err)
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)

    try {
      const updated = await partnersAdminApi.updatePartner(partnerId, editForm)
      setPartner(updated)
      setEditing(false)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || "Failed to update partner")
      setTraceId(apiError.trace_id || null)
    } finally {
      setSaving(false)
    }
  }

  const handleUpdateCEO = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)

    try {
      const updated = await partnersAdminApi.updatePartner(partnerId, {
        ceo_name: ceoForm.ceo_name || null,
        ceo_title: ceoForm.ceo_title || null,
        ceo_quote: ceoForm.ceo_quote || null,
        ceo_bio_markdown: ceoForm.ceo_bio_markdown || null,
        ceo_photo_media_id: ceoForm.ceo_photo_media_id,
      })
      setPartner(updated)
      setCeoEditing(false)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || "Failed to update CEO module")
      setTraceId(apiError.trace_id || null)
    } finally {
      setSaving(false)
    }
  }

  const handleSaveOffers = async () => {
    setSavingOffers(true)
    setError(null)

    try {
      const offerIds = primaryOfferId ? [primaryOfferId, ...additionalOfferIds.filter(id => id !== primaryOfferId)] : additionalOfferIds
      await partnersAdminApi.linkPartnerOffers(partnerId, {
        primary_offer_id: primaryOfferId,
        offer_ids: offerIds,
      })
      await loadPartner()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || "Failed to link offers")
      setTraceId(apiError.trace_id || null)
    } finally {
      setSavingOffers(false)
    }
  }

  const handleUploadMedia = async (file: File, type: 'IMAGE' | 'VIDEO') => {
    if (!partnerId) return
    
    setUploadingMedia(true)
    setError(null)

    try {
      // Step 1: Get presigned URL
      const presignResponse = await partnersAdminApi.presignPartnerUpload(
        partnerId,
        'media',
        file.name,
        file.type,
        file.size,
        type
      )

      // Step 2: Upload to S3
      const uploadResponse = await fetch(presignResponse.upload_url, {
        method: 'PUT',
        headers: presignResponse.required_headers,
        body: file,
      })

      if (!uploadResponse.ok) {
        throw new Error(`Upload failed: ${uploadResponse.statusText}`)
      }

      // Step 3: Create metadata
      await partnersAdminApi.createPartnerMedia(partnerId, {
        key: presignResponse.key,
        mime_type: file.type,
        size_bytes: file.size,
        media_type: type,
      })

      await loadPartner()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to upload media")
    } finally {
      setUploadingMedia(false)
    }
  }

  const handleUploadDocument = async (file: File, title: string) => {
    if (!partnerId) return
    
    setUploadingDocument(true)
    setError(null)

    try {
      // Get presigned URL
      const presignResponse = await partnersAdminApi.presignPartnerUpload(
        partnerId,
        'document',
        file.name,
        file.type,
        file.size
      )

      // Upload to S3
      const uploadResponse = await fetch(presignResponse.upload_url, {
        method: 'PUT',
        headers: presignResponse.required_headers,
        body: file,
      })

      if (!uploadResponse.ok) {
        throw new Error(`Upload failed: ${uploadResponse.statusText}`)
      }

      // Determine document type from extension
      const ext = file.name.split('.').pop()?.toLowerCase() || 'OTHER'
      let docType: 'PDF' | 'DOC' | 'OTHER' = 'OTHER'
      if (ext === 'pdf') docType = 'PDF'
      else if (['doc', 'docx'].includes(ext)) docType = 'DOC'

      // Create metadata
      await partnersAdminApi.createPartnerDocument(partnerId, {
        title,
        key: presignResponse.key,
        mime_type: file.type,
        size_bytes: file.size,
        document_type: docType,
      })

      await loadPartner()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to upload document")
    } finally {
      setUploadingDocument(false)
    }
  }

  const handleDeleteMedia = async (mediaId: string) => {
    if (!partnerId || !confirm('Delete this media item?')) return

    try {
      await partnersAdminApi.deletePartnerMedia(partnerId, mediaId)
      await loadPartner()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to delete media")
    }
  }

  const handleDeleteDocument = async (docId: string) => {
    if (!partnerId || !confirm('Delete this document?')) return

    try {
      await partnersAdminApi.deletePartnerDocument(partnerId, docId)
      await loadPartner()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to delete document")
    }
  }

  const handleStatusAction = async (action: 'publish' | 'archive') => {
    try {
      if (action === 'publish') {
        await partnersAdminApi.publishPartner(partnerId)
      } else {
        await partnersAdminApi.archivePartner(partnerId)
      }
      await loadPartner()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || `Failed to ${action} partner`)
      setTraceId(apiError.trace_id || null)
    }
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      DRAFT: "bg-gray-100 text-gray-800",
      PUBLISHED: "bg-green-100 text-green-800",
      ARCHIVED: "bg-red-100 text-red-800",
    }
    return colors[status as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  const filteredOffers = availableOffers.filter(offer => 
    offer.name.toLowerCase().includes(offerSearchQuery.toLowerCase()) ||
    offer.code.toLowerCase().includes(offerSearchQuery.toLowerCase())
  )

  if (loading && !partner) {
    return (
      <main className="container mx-auto p-8">
        <p className="text-gray-500">Loading...</p>
      </main>
    )
  }

  if (!partner) {
    return (
      <main className="container mx-auto p-8">
        <p className="text-red-500">Partner not found</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8 max-w-7xl">
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/partners" className="text-blue-600 hover:underline mb-2 inline-block">← Back to Partners</Link>
          <h1 className="text-3xl font-bold">{partner.trade_name || partner.legal_name}</h1>
          <p className="text-gray-600">{partner.code}</p>
        </div>
        <div className="flex gap-2 items-center">
          <span className={`px-3 py-1 text-sm font-semibold rounded-full ${getStatusBadge(partner.status)}`}>
            {partner.status}
          </span>
          {partner.status === 'DRAFT' && (
            <button
              onClick={() => handleStatusAction('publish')}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
            >
              Publish
            </button>
          )}
          {partner.status === 'PUBLISHED' && (
            <button
              onClick={() => handleStatusAction('archive')}
              className="bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700"
            >
              Archive
            </button>
          )}
          {partner.status === 'ARCHIVED' && (
            <button
              onClick={() => handleStatusAction('publish')}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              Republish
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800 font-medium">{error}</div>
          {traceId && <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex space-x-8">
          {(['overview', 'ceo', 'offers', 'team', 'media', 'documents', 'portfolio'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab === 'ceo' ? 'CEO Module' : tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Overview</h2>
            <button
              onClick={() => setEditing(!editing)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              {editing ? "Cancel" : "Edit"}
            </button>
          </div>

          {editing ? (
            <form onSubmit={handleUpdate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Code</label>
                  <input
                    type="text"
                    value={editForm.code || ""}
                    onChange={(e) => setEditForm({ ...editForm, code: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Legal Name</label>
                  <input
                    type="text"
                    value={editForm.legal_name || ""}
                    onChange={(e) => setEditForm({ ...editForm, legal_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Trade Name</label>
                <input
                  type="text"
                  value={editForm.trade_name || ""}
                  onChange={(e) => setEditForm({ ...editForm, trade_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description (Markdown)</label>
                <textarea
                  value={editForm.description_markdown || ""}
                  onChange={(e) => setEditForm({ ...editForm, description_markdown: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows={6}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Website URL</label>
                  <input
                    type="url"
                    value={editForm.website_url || ""}
                    onChange={(e) => setEditForm({ ...editForm, website_url: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                  <input
                    type="text"
                    value={editForm.city || ""}
                    onChange={(e) => setEditForm({ ...editForm, city: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
                <input
                  type="text"
                  value={editForm.country || ""}
                  onChange={(e) => setEditForm({ ...editForm, country: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Contact Email</label>
                <input
                  type="email"
                  value={editForm.contact_email || ""}
                  onChange={(e) => setEditForm({ ...editForm, contact_email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <button
                type="submit"
                disabled={saving}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </form>
          ) : (
            <div className="space-y-4">
              <div><strong>Legal Name:</strong> {partner.legal_name}</div>
              <div><strong>Trade Name:</strong> {partner.trade_name || "-"}</div>
              <div><strong>Website:</strong> {partner.website_url ? <a href={partner.website_url} target="_blank" rel="noreferrer" className="text-blue-600">{partner.website_url}</a> : "-"}</div>
              <div><strong>Location:</strong> {partner.city && partner.country ? `${partner.city}, ${partner.country}` : "-"}</div>
              {partner.description_markdown && (
                <div>
                  <strong>Description:</strong>
                  <div className="mt-2"><MarkdownProse content={partner.description_markdown} /></div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'ceo' && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">CEO Module</h2>
            <button
              onClick={() => setCeoEditing(!ceoEditing)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              {ceoEditing ? "Cancel" : "Edit"}
            </button>
          </div>

          {ceoEditing ? (
            <form onSubmit={handleUpdateCEO} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">CEO Name</label>
                  <input
                    type="text"
                    value={ceoForm.ceo_name}
                    onChange={(e) => setCeoForm({ ...ceoForm, ceo_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">CEO Title</label>
                  <input
                    type="text"
                    value={ceoForm.ceo_title}
                    onChange={(e) => setCeoForm({ ...ceoForm, ceo_title: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">CEO Quote (max 240 chars)</label>
                <textarea
                  value={ceoForm.ceo_quote}
                  onChange={(e) => setCeoForm({ ...ceoForm, ceo_quote: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows={3}
                  maxLength={240}
                />
                <p className="text-sm text-gray-500 mt-1">{ceoForm.ceo_quote.length}/240</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">CEO Bio (Markdown)</label>
                <textarea
                  value={ceoForm.ceo_bio_markdown}
                  onChange={(e) => setCeoForm({ ...ceoForm, ceo_bio_markdown: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  rows={8}
                />
              </div>
              {partner.media.filter(m => m.type === 'IMAGE').length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">CEO Photo</label>
                  <select
                    value={ceoForm.ceo_photo_media_id || ""}
                    onChange={(e) => setCeoForm({ ...ceoForm, ceo_photo_media_id: e.target.value || null })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  >
                    <option value="">No photo</option>
                    {partner.media.filter(m => m.type === 'IMAGE').map(media => (
                      <option key={media.id} value={media.id}>Image {media.id.substring(0, 8)}</option>
                    ))}
                  </select>
                </div>
              )}
              <button
                type="submit"
                disabled={saving}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save CEO Module"}
              </button>
            </form>
          ) : (
            <div className="space-y-4">
              {partner.ceo_photo_url && (
                <img src={partner.ceo_photo_url} alt="CEO" className="w-32 h-32 rounded-full object-cover" />
              )}
              <div><strong>Name:</strong> {partner.ceo_name || "-"}</div>
              <div><strong>Title:</strong> {partner.ceo_title || "-"}</div>
              {partner.ceo_quote && (
                <div>
                  <strong>Quote:</strong>
                  <blockquote className="border-l-4 pl-4 italic text-gray-700 mt-2">{partner.ceo_quote}</blockquote>
                </div>
              )}
              {partner.ceo_bio_markdown && (
                <div>
                  <strong>Bio:</strong>
                  <div className="mt-2"><MarkdownProse content={partner.ceo_bio_markdown} /></div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'offers' && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Linked Offers</h2>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Search Offers</label>
            <input
              type="text"
              placeholder="Search by name or code..."
              value={offerSearchQuery}
              onChange={(e) => setOfferSearchQuery(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Primary Offer</label>
            <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-md">
              {filteredOffers.map(offer => (
                <div
                  key={offer.id}
                  className={`p-3 border-b cursor-pointer hover:bg-blue-50 ${
                    primaryOfferId === offer.id ? 'bg-blue-100' : ''
                  }`}
                  onClick={() => setPrimaryOfferId(offer.id === primaryOfferId ? null : offer.id)}
                >
                  <input
                    type="radio"
                    checked={primaryOfferId === offer.id}
                    onChange={() => setPrimaryOfferId(offer.id === primaryOfferId ? null : offer.id)}
                    className="mr-2"
                  />
                  <span className="font-medium">{offer.name}</span> ({offer.code})
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={handleSaveOffers}
            disabled={savingOffers}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {savingOffers ? "Saving..." : "Save Links"}
          </button>
        </div>
      )}

      {activeTab === 'media' && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Media</h2>
          
          <div className="mb-4 flex gap-4">
            <input
              type="file"
              ref={imageFileInputRef}
              accept="image/*"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleUploadMedia(file, 'IMAGE')
              }}
              className="hidden"
            />
            <input
              type="file"
              ref={videoFileInputRef}
              accept="video/*"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleUploadMedia(file, 'VIDEO')
              }}
              className="hidden"
            />
            <button
              onClick={() => imageFileInputRef.current?.click()}
              disabled={uploadingMedia}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {uploadingMedia ? "Uploading..." : "Upload Image"}
            </button>
            <button
              onClick={() => videoFileInputRef.current?.click()}
              disabled={uploadingMedia}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {uploadingMedia ? "Uploading..." : "Upload Video"}
            </button>
          </div>

          <div className="grid grid-cols-4 gap-4">
            {partner.media.map(media => (
              <div key={media.id} className="border rounded-lg p-2">
                {media.type === 'IMAGE' && media.url && (
                  <img src={media.url} alt="" className="w-full h-32 object-cover rounded" />
                )}
                {media.type === 'VIDEO' && (
                  <div className="w-full h-32 bg-gray-200 rounded flex items-center justify-center">
                    <span className="text-gray-500">Video</span>
                  </div>
                )}
                <div className="mt-2">
                  <button
                    onClick={() => handleDeleteMedia(media.id)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Delete
                  </button>
                  {media.type === 'IMAGE' && media.id === partner.ceo_photo_media_id && (
                    <span className="ml-2 text-xs text-green-600">CEO Photo</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'documents' && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Documents</h2>
          
          <div className="mb-4">
            <input
              type="file"
              ref={documentFileInputRef}
              accept=".pdf,.doc,.docx"
              onChange={async (e) => {
                const file = e.target.files?.[0]
                if (file) {
                  const title = prompt("Document title:", file.name)
                  if (title) await handleUploadDocument(file, title)
                }
              }}
              className="hidden"
            />
            <button
              onClick={() => documentFileInputRef.current?.click()}
              disabled={uploadingDocument}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {uploadingDocument ? "Uploading..." : "Upload Document"}
            </button>
          </div>

          <div className="space-y-2">
            {partner.documents.map(doc => (
              <div key={doc.id} className="flex justify-between items-center p-3 border rounded-lg">
                <div>
                  <strong>{doc.title}</strong>
                  <span className="ml-2 text-sm text-gray-500">({doc.type})</span>
                  {doc.url && (
                    <a href={doc.url} target="_blank" rel="noreferrer" className="ml-2 text-blue-600 hover:underline text-sm">
                      Download
                    </a>
                  )}
                </div>
                <button
                  onClick={() => handleDeleteDocument(doc.id)}
                  className="text-red-600 hover:text-red-800 text-sm"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'team' && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Team Members</h2>
          <p className="text-gray-500 mb-4">Team management coming soon...</p>
          {partner.team_members.length > 0 && (
            <div className="space-y-4">
              {partner.team_members.map(member => (
                <div key={member.id} className="border rounded-lg p-4">
                  <div className="flex items-center gap-4">
                    {member.photo_url && (
                      <img src={member.photo_url} alt={member.full_name} className="w-16 h-16 rounded-full object-cover" />
                    )}
                    <div>
                      <strong>{member.full_name}</strong>
                      {member.role_title && <div className="text-gray-600">{member.role_title}</div>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'portfolio' && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Portfolio Projects</h2>
          <p className="text-gray-500 mb-4">Portfolio management coming soon...</p>
          {partner.portfolio_projects.length > 0 && (
            <div className="space-y-4">
              {partner.portfolio_projects.map(project => (
                <div key={project.id} className="border rounded-lg p-4">
                  <strong>{project.title}</strong>
                  {project.category && <span className="ml-2 text-gray-600">({project.category})</span>}
                  {project.short_summary && <p className="text-sm text-gray-500 mt-2">{project.short_summary}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </main>
  )
}

