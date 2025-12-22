"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { articlesAdminApi, parseApiError, type CreateArticlePayload } from "@/lib/api"

export default function NewArticlePage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  
  const [form, setForm] = useState<CreateArticlePayload>({
    slug: "",
    title: "",
    subtitle: "",
    excerpt: "",
    content_markdown: "",
    author_name: "",
    seo_title: "",
    seo_description: "",
    tags: [],
    is_featured: false,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError(null)
    setTraceId(null)

    try {
      // Generate slug from title if not provided
      let slug = form.slug.trim()
      if (!slug && form.title) {
        slug = form.title
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/^-+|-+$/g, '')
      }
      
      if (!slug) {
        setError("Slug is required")
        setCreating(false)
        return
      }

      const payload: CreateArticlePayload = {
        ...form,
        slug,
        tags: form.tags || [],
      }
      const newArticle = await articlesAdminApi.createArticle(payload)
      router.push(`/articles/${newArticle.id}`)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || "Failed to create article")
      setTraceId(apiError.trace_id || null)
    } finally {
      setCreating(false)
    }
  }

  const generateSlugFromTitle = () => {
    if (form.title) {
      const slug = form.title
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
      setForm({ ...form, slug })
    }
  }

  return (
    <main className="container mx-auto p-8 max-w-3xl">
      <div className="mb-6">
        <Link href="/articles" className="text-blue-600 hover:underline text-sm">
          ← Back to Articles
        </Link>
      </div>

      <h1 className="text-3xl font-bold text-gray-900 mb-6">Create New Article</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800 font-medium">{error}</div>
          {traceId && (
            <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
          )}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              onBlur={generateSlugFromTitle}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Article Title"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Slug <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              placeholder="url-friendly-slug"
            />
            <p className="text-xs text-gray-500 mt-1">URL-friendly identifier (auto-generated from title if empty)</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Subtitle
            </label>
            <input
              type="text"
              value={form.subtitle || ""}
              onChange={(e) => setForm({ ...form, subtitle: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Optional subtitle"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Excerpt
            </label>
            <textarea
              value={form.excerpt || ""}
              onChange={(e) => setForm({ ...form, excerpt: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              placeholder="Short summary for cards..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Author Name
            </label>
            <input
              type="text"
              value={form.author_name || ""}
              onChange={(e) => setForm({ ...form, author_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Author name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Content (Markdown)
            </label>
            <textarea
              value={form.content_markdown || ""}
              onChange={(e) => setForm({ ...form, content_markdown: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              rows={12}
              placeholder="# Article Content

Write your article content in Markdown format...

## Section 1

Your content here..."
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                SEO Title
              </label>
              <input
                type="text"
                value={form.seo_title || ""}
                onChange={(e) => setForm({ ...form, seo_title: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="SEO title (defaults to title)"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tags (comma-separated)
              </label>
              <input
                type="text"
                value={(form.tags || []).join(', ')}
                onChange={(e) => {
                  const tags = e.target.value.split(',').map(t => t.trim()).filter(t => t)
                  setForm({ ...form, tags })
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="tag1, tag2, tag3"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              SEO Description
            </label>
            <textarea
              value={form.seo_description || ""}
              onChange={(e) => setForm({ ...form, seo_description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
              placeholder="SEO meta description..."
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_featured"
              checked={form.is_featured || false}
              onChange={(e) => setForm({ ...form, is_featured: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="is_featured" className="ml-2 block text-sm text-gray-700">
              Featured (show in blog hero)
            </label>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              disabled={creating}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {creating ? "Creating..." : "Create Article"}
            </button>
            <Link
              href="/articles"
              className="bg-gray-200 text-gray-800 px-6 py-2 rounded-lg hover:bg-gray-300 transition-colors inline-block text-center"
            >
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </main>
  )
}

