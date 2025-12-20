"use client"

import { useEffect, useState, useRef } from "react"
import { useRouter, useParams } from "next/navigation"
import Link from "next/link"
import { articlesAdminApi, offersAdminApi, systemApi, parseApiError, type Article, type UpdateArticlePayload, type Offer } from "@/lib/api"
import { MarkdownProse } from "@/components/MarkdownProse"
import { insertAtCursor } from "@/utils/markdownEditor"

export default function ArticleDetailPage() {
  const router = useRouter()
  const params = useParams()
  const articleId = params.id as string
  
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState<UpdateArticlePayload>({})
  const [saving, setSaving] = useState(false)

  // Media state
  const [media, setMedia] = useState<Array<{
    id: string
    type: 'image' | 'video' | 'document'
    url?: string
    mime_type: string
    size_bytes: number
    width?: number
    height?: number
    created_at: string
  }>>([])
  const [mediaLoading, setMediaLoading] = useState(false)
  const [mediaError, setMediaError] = useState<string | null>(null)
  const [uploadingMedia, setUploadingMedia] = useState(false)
  const imageFileInputRef = useRef<HTMLInputElement>(null)
  const videoFileInputRef = useRef<HTMLInputElement>(null)
  const documentFileInputRef = useRef<HTMLInputElement>(null)
  const markdownTextareaRef = useRef<HTMLTextAreaElement>(null)

  // Offers linking state
  const [availableOffers, setAvailableOffers] = useState<Offer[]>([])
  const [selectedOfferIds, setSelectedOfferIds] = useState<string[]>([])
  const [savingOffers, setSavingOffers] = useState(false)

  // Storage status
  const [storageEnabled, setStorageEnabled] = useState<boolean | null>(null)
  const [storageLoading, setStorageLoading] = useState(false)

  useEffect(() => {
    if (articleId) {
      loadArticle()
      loadMedia()
      loadAvailableOffers()
      loadStorageStatus()
    }
  }, [articleId])

  const loadStorageStatus = async () => {
    setStorageLoading(true)
    try {
      const info = await systemApi.getStorageInfo()
      setStorageEnabled(info.enabled)
    } catch {
      setStorageEnabled(false)
    } finally {
      setStorageLoading(false)
    }
  }

  const loadArticle = async () => {
    setLoading(true)
    setError(null)
    setTraceId(null)
    
    try {
      const data = await articlesAdminApi.getArticle(articleId)
      setArticle(data)
      setEditForm({
        title: data.title,
        subtitle: data.subtitle || "",
        excerpt: data.excerpt || "",
        content_markdown: data.content_markdown || "",
        author_name: data.author_name || "",
        seo_title: data.seo_title || "",
        seo_description: data.seo_description || "",
        tags: data.tags || [],
        is_featured: data.is_featured,
        status: data.status as any,
      })
      setSelectedOfferIds(data.offer_ids || [])
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || "Failed to load article")
      setTraceId(apiError.trace_id || null)
    } finally {
      setLoading(false)
    }
  }

  const loadMedia = async () => {
    if (!articleId) return
    
    setMediaLoading(true)
    setMediaError(null)
    
    try {
      const data = await articlesAdminApi.listArticleMedia(articleId)
      setMedia(data)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setMediaError(apiError.message || "Failed to load media")
    } finally {
      setMediaLoading(false)
    }
  }

  const loadAvailableOffers = async () => {
    try {
      const offers = await offersAdminApi.listOffers({ limit: 200 })
      setAvailableOffers(offers)
    } catch (err) {
      console.error('Failed to load offers:', err)
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setTraceId(null)

    try {
      const updated = await articlesAdminApi.updateArticle(articleId, editForm)
      setArticle(updated)
      setEditing(false)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || "Failed to update article")
      setTraceId(apiError.trace_id || null)
    } finally {
      setSaving(false)
    }
  }

  const handleStatusAction = async (action: 'publish' | 'archive') => {
    try {
      let updated: Article
      if (action === 'publish') {
        updated = await articlesAdminApi.publishArticle(articleId)
      } else {
        updated = await articlesAdminApi.archiveArticle(articleId)
      }
      setArticle(updated)
      loadArticle()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || `Failed to ${action} article`)
      setTraceId(apiError.trace_id || null)
    }
  }

  const handleMediaUpload = async (files: FileList | null, type: 'image' | 'video' | 'document') => {
    if (storageEnabled === false || !files || files.length === 0 || !articleId) return
    
    setUploadingMedia(true)
    setMediaError(null)

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        
        // Step 1: Presign
        const presignResponse = await articlesAdminApi.presignArticleUpload(articleId, {
          upload_type: type,
          file_name: file.name,
          mime_type: file.type,
          size_bytes: file.size,
        })

        // Step 2: PUT to S3
        const uploadResponse = await fetch(presignResponse.upload_url, {
          method: 'PUT',
          headers: presignResponse.required_headers,
          body: file,
        })

        if (!uploadResponse.ok) {
          throw new Error(`Upload failed: ${uploadResponse.statusText}`)
        }

        // Step 3: Create metadata (simplified - no width/height detection for now)
        await articlesAdminApi.createArticleMedia(articleId, {
          key: presignResponse.key,
          mime_type: file.type,
          size_bytes: file.size,
          type: type,
        })
      }

      await loadMedia()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setMediaError(apiError.message || "Failed to upload media")
    } finally {
      setUploadingMedia(false)
    }
  }

  const handleDeleteMedia = async (mediaId: string) => {
    if (!articleId || !confirm('Delete this media item?')) return

    try {
      await articlesAdminApi.deleteArticleMedia(articleId, mediaId)
      await loadMedia()
      await loadArticle() // Refresh article to update cover_media_id/promo_video_media_id
    } catch (err: any) {
      const apiError = parseApiError(err)
      setMediaError(apiError.message || "Failed to delete media")
    }
  }

  const handleSetCover = async (mediaId: string) => {
    if (!articleId) return

    try {
      await articlesAdminApi.setArticleCover(articleId, mediaId)
      await loadArticle()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setMediaError(apiError.message || "Failed to set cover")
    }
  }

  const handleSetPromoVideo = async (mediaId: string) => {
    if (!articleId) return

    try {
      await articlesAdminApi.setArticlePromoVideo(articleId, mediaId)
      await loadArticle()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setMediaError(apiError.message || "Failed to set promo video")
    }
  }

  const handleSaveOffers = async () => {
    if (!articleId) return
    setSavingOffers(true)
    setError(null)

    try {
      await articlesAdminApi.linkArticleOffers(articleId, selectedOfferIds)
      await loadArticle()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to link offers")
    } finally {
      setSavingOffers(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      draft: "bg-gray-100 text-gray-800",
      published: "bg-green-100 text-green-800",
      archived: "bg-red-100 text-red-800",
    }
    return colors[status as keyof typeof colors] || "bg-gray-100 text-gray-800"
  }

  const handleInsertMediaIntoContent = (mediaItem: { type: string; url?: string; id: string }) => {
    if (!markdownTextareaRef.current || !mediaItem.url) {
      return
    }

    let markdown = ""
    if (mediaItem.type === 'image') {
      markdown = `![alt text](${mediaItem.url})\n`
    } else if (mediaItem.type === 'video') {
      markdown = `${mediaItem.url}\n`
    } else if (mediaItem.type === 'document') {
      markdown = `[Download document](${mediaItem.url})\n`
    }

    if (markdown) {
      insertAtCursor(markdownTextareaRef.current, markdown)
    }
  }

  const formatDateTime = (dateString: string | undefined): string => {
    if (!dateString) return "-"
    try {
      return new Date(dateString).toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return "-"
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (loading && !article) {
    return (
      <main className="container mx-auto p-8">
        <p className="text-gray-500">Loading...</p>
      </main>
    )
  }

  if (!article) {
    return (
      <main className="container mx-auto p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">Article not found</div>
        </div>
      </main>
    )
  }

  const coverMedia = media.find(m => m.id === article.cover_media_id)
  const promoVideoMedia = media.find(m => m.id === article.promo_video_media_id)
  const galleryMedia = media.filter(m => 
    m.id !== article.cover_media_id && 
    m.id !== article.promo_video_media_id &&
    m.type !== 'document'
  )
  const documentMedia = media.filter(m => m.type === 'document')

  return (
    <main className="container mx-auto p-8 max-w-6xl">
      <div className="mb-6">
        <Link href="/articles" className="text-blue-600 hover:underline text-sm">
          ← Back to Articles
        </Link>
      </div>

      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{article.title}</h1>
          <div className="flex gap-2 mt-2">
            <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadge(article.status)}`}>
              {article.status}
            </span>
            {article.is_featured && (
              <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                Featured
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {article.status === 'draft' && (
            <button
              onClick={() => handleStatusAction('publish')}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
            >
              Publish
            </button>
          )}
          {article.status === 'published' && (
            <button
              onClick={() => handleStatusAction('archive')}
              className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
            >
              Archive
            </button>
          )}
          {article.status === 'archived' && (
            <button
              onClick={() => handleStatusAction('publish')}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
            >
              Republish
            </button>
          )}
          <button
            onClick={() => setEditing(!editing)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            {editing ? "Cancel" : "Edit"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800 font-medium">{error}</div>
          {traceId && (
            <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
          )}
        </div>
      )}

      {/* Edit Form */}
      {editing && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Edit Article</h2>
          <form onSubmit={handleUpdate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
              <input
                type="text"
                value={editForm.title || ""}
                onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Subtitle</label>
              <input
                type="text"
                value={editForm.subtitle || ""}
                onChange={(e) => setEditForm({ ...editForm, subtitle: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Excerpt</label>
              <textarea
                value={editForm.excerpt || ""}
                onChange={(e) => setEditForm({ ...editForm, excerpt: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Content (Markdown)</label>
              
              {/* Toolbar */}
              <div className="flex flex-wrap gap-2 mb-2 p-2 bg-gray-50 rounded-t-lg border border-gray-300 border-b-0">
                <button
                  type="button"
                  onClick={() => {
                    if (markdownTextareaRef.current) {
                      insertAtCursor(markdownTextareaRef.current, "", "## ", undefined, "## ")
                    }
                  }}
                  className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-100"
                  title="Heading 2"
                >
                  H2
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (markdownTextareaRef.current) {
                      insertAtCursor(markdownTextareaRef.current, "", "**", "**")
                    }
                  }}
                  className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-100 font-bold"
                  title="Bold"
                >
                  <strong>B</strong>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (markdownTextareaRef.current) {
                      insertAtCursor(markdownTextareaRef.current, "", "*", "*")
                    }
                  }}
                  className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-100 italic"
                  title="Italic"
                >
                  <em>I</em>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const url = prompt("Enter URL:")
                    const text = prompt("Enter link text:", "") || url || ""
                    if (url && markdownTextareaRef.current) {
                      insertAtCursor(markdownTextareaRef.current, `[${text}](${url})`)
                    }
                  }}
                  className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-100"
                  title="Link"
                >
                  Link
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (markdownTextareaRef.current) {
                      insertAtCursor(markdownTextareaRef.current, "", "- ", undefined, "- ")
                    }
                  }}
                  className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-100"
                  title="Bullet List"
                >
                  • List
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (markdownTextareaRef.current) {
                      insertAtCursor(markdownTextareaRef.current, "", "> ", undefined, "> ")
                    }
                  }}
                  className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-100"
                  title="Quote"
                >
                  Quote
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (markdownTextareaRef.current) {
                      insertAtCursor(markdownTextareaRef.current, "\n---\n")
                    }
                  }}
                  className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-100"
                  title="Divider"
                >
                  ───
                </button>
              </div>

              {/* Editor + Preview side-by-side */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Editor */}
                <div className="border border-gray-300 rounded-b-lg">
                  <textarea
                    ref={markdownTextareaRef}
                    value={editForm.content_markdown || ""}
                    onChange={(e) => setEditForm({ ...editForm, content_markdown: e.target.value })}
                    className="w-full h-[600px] px-3 py-2 border-0 rounded-b-lg font-mono text-sm resize-none focus:outline-none"
                    placeholder="Write your markdown here..."
                  />
                </div>

                {/* Live Preview */}
                <div className="border border-gray-300 rounded-lg p-4 bg-white overflow-y-auto h-[600px]">
                  <div className="text-xs text-gray-500 mb-2 font-semibold">LIVE PREVIEW</div>
                  <MarkdownProse content={editForm.content_markdown || ""} />
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Author</label>
                <input
                  type="text"
                  value={editForm.author_name || ""}
                  onChange={(e) => setEditForm({ ...editForm, author_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={(editForm.tags || []).join(', ')}
                  onChange={(e) => {
                    const tags = e.target.value.split(',').map(t => t.trim()).filter(t => t)
                    setEditForm({ ...editForm, tags })
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={editForm.is_featured || false}
                onChange={(e) => setEditForm({ ...editForm, is_featured: e.target.checked })}
                className="h-4 w-4"
              />
              <label className="ml-2 text-sm text-gray-700">Featured</label>
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={saving}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Article Info */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Article Information</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="font-medium text-gray-700">Slug:</span> {article.slug}
          </div>
          <div>
            <span className="font-medium text-gray-700">Published:</span> {formatDateTime(article.published_at)}
          </div>
          <div>
            <span className="font-medium text-gray-700">Author:</span> {article.author_name || "-"}
          </div>
          <div>
            <span className="font-medium text-gray-700">Created:</span> {formatDateTime(article.created_at)}
          </div>
          {article.tags.length > 0 && (
            <div className="col-span-2">
              <span className="font-medium text-gray-700">Tags:</span> {article.tags.join(', ')}
            </div>
          )}
        </div>
      </div>

      {/* Media Section */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Media</h2>
        
        {storageEnabled === false && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
            <div className="text-yellow-800 text-sm">
              ⚠️ Storage not configured. Uploads disabled.
            </div>
          </div>
        )}

        {mediaError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <div className="text-red-800 text-sm">{mediaError}</div>
          </div>
        )}

        <div className="mb-4 flex gap-2">
          <input
            type="file"
            ref={imageFileInputRef}
            accept="image/*"
            multiple
            onChange={(e) => handleMediaUpload(e.target.files, 'image')}
            className="hidden"
          />
          <input
            type="file"
            ref={videoFileInputRef}
            accept="video/*"
            onChange={(e) => handleMediaUpload(e.target.files, 'video')}
            className="hidden"
          />
          <input
            type="file"
            ref={documentFileInputRef}
            accept="application/pdf"
            multiple
            onChange={(e) => handleMediaUpload(e.target.files, 'document')}
            className="hidden"
          />
          <button
            onClick={() => imageFileInputRef.current?.click()}
            disabled={uploadingMedia || storageEnabled === false}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            {uploadingMedia ? "Uploading..." : "Upload Images"}
          </button>
          <button
            onClick={() => videoFileInputRef.current?.click()}
            disabled={uploadingMedia || storageEnabled === false}
            className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:opacity-50 text-sm"
          >
            {uploadingMedia ? "Uploading..." : "Upload Video"}
          </button>
          <button
            onClick={() => documentFileInputRef.current?.click()}
            disabled={uploadingMedia || storageEnabled === false}
            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 disabled:opacity-50 text-sm"
          >
            {uploadingMedia ? "Uploading..." : "Upload Documents"}
          </button>
        </div>

        {mediaLoading ? (
          <div className="text-center py-8 text-gray-500">Loading media...</div>
        ) : (
          <div className="space-y-4">
            {coverMedia && (
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium">Cover Image</h3>
                </div>
                {coverMedia.url && (
                  <img src={coverMedia.url} alt="Cover" className="w-full h-64 object-cover rounded" />
                )}
                <div className="mt-2 flex gap-2">
                  <button
                    onClick={() => handleInsertMediaIntoContent(coverMedia)}
                    className="text-sm text-blue-600 hover:text-blue-800"
                    disabled={!coverMedia.url}
                  >
                    Insert into Content
                  </button>
                  <button
                    onClick={() => handleDeleteMedia(coverMedia.id)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </div>
              </div>
            )}

            {promoVideoMedia && (
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium">Promo Video</h3>
                </div>
                {promoVideoMedia.url && (
                  <video src={promoVideoMedia.url} controls className="w-full rounded" />
                )}
                <div className="mt-2 flex gap-2">
                  <button
                    onClick={() => handleInsertMediaIntoContent(promoVideoMedia)}
                    className="text-sm text-blue-600 hover:text-blue-800"
                    disabled={!promoVideoMedia.url}
                  >
                    Insert into Content
                  </button>
                  <button
                    onClick={() => handleDeleteMedia(promoVideoMedia.id)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </div>
              </div>
            )}

            {galleryMedia.length > 0 && (
              <div className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-medium mb-4">Gallery ({galleryMedia.length})</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {galleryMedia.map((item) => (
                    <div key={item.id} className="relative">
                      {item.type === 'image' && item.url && (
                        <img src={item.url} alt="" className="w-full h-32 object-cover rounded" />
                      )}
                      {item.type === 'video' && item.url && (
                        <video src={item.url} className="w-full h-32 object-cover rounded" />
                      )}
                      <div className="mt-2 flex gap-2 flex-wrap">
                        <button
                          onClick={() => handleInsertMediaIntoContent(item)}
                          className="text-xs text-green-600 hover:text-green-800"
                          disabled={!item.url}
                        >
                          Insert
                        </button>
                        {item.type === 'image' && (
                          <button
                            onClick={() => handleSetCover(item.id)}
                            className="text-xs text-blue-600 hover:text-blue-800"
                          >
                            Set Cover
                          </button>
                        )}
                        {item.type === 'video' && (
                          <button
                            onClick={() => handleSetPromoVideo(item.id)}
                            className="text-xs text-purple-600 hover:text-purple-800"
                          >
                            Set Promo
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteMedia(item.id)}
                          className="text-xs text-red-600 hover:text-red-800"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {documentMedia.length > 0 && (
              <div className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-medium mb-4">Documents ({documentMedia.length})</h3>
                <div className="space-y-2">
                  {documentMedia.map((item) => (
                    <div key={item.id} className="flex items-center justify-between p-2 border border-gray-200 rounded">
                      <span className="text-sm">{item.mime_type} ({formatFileSize(item.size_bytes)})</span>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleInsertMediaIntoContent(item)}
                          className="text-sm text-green-600 hover:text-green-800"
                          disabled={!item.url}
                        >
                          Insert
                        </button>
                        <button
                          onClick={() => handleDeleteMedia(item.id)}
                          className="text-sm text-red-600 hover:text-red-800"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {media.length === 0 && (
              <div className="text-center py-8 text-gray-500">No media uploaded yet</div>
            )}
          </div>
        )}
      </div>

      {/* Link to Offers */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Linked Offers</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select offers to link to this article (multi-select)
          </label>
          <select
            multiple
            value={selectedOfferIds}
            onChange={(e) => {
              const selected = Array.from(e.target.selectedOptions, opt => opt.value)
              setSelectedOfferIds(selected)
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-md min-h-[200px]"
            size={10}
          >
            {availableOffers.map((offer) => (
              <option key={offer.id} value={offer.id}>
                {offer.code} - {offer.name}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Hold Ctrl (Cmd on Mac) to select multiple offers
          </p>
        </div>
        <button
          onClick={handleSaveOffers}
          disabled={savingOffers}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {savingOffers ? "Saving..." : "Save Links"}
        </button>
        {article.offer_ids.length > 0 && (
          <div className="mt-4">
            <p className="text-sm text-gray-700 mb-2">Currently linked offers:</p>
            <ul className="list-disc list-inside text-sm text-gray-600">
              {article.offer_ids.map(offerId => {
                const offer = availableOffers.find(o => o.id === offerId)
                return offer ? (
                  <li key={offerId}>{offer.code} - {offer.name}</li>
                ) : (
                  <li key={offerId}>{offerId}</li>
                )
              })}
            </ul>
          </div>
        )}
      </div>

      {/* Content Preview */}
      {article.content_markdown && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Content Preview</h2>
          <div className="prose max-w-none">
            <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded">
              {article.content_markdown}
            </pre>
          </div>
        </div>
      )}
    </main>
  )
}

