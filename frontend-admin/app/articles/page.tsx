"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { articlesAdminApi, parseApiError, type ArticleListItem } from "@/lib/api"

export default function ArticlesPage() {
  const router = useRouter()
  const [articles, setArticles] = useState<ArticleListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [featuredFilter, setFeaturedFilter] = useState<string>("")
  const [searchQuery, setSearchQuery] = useState<string>("")

  useEffect(() => {
    loadArticles()
  }, [statusFilter, featuredFilter, searchQuery])

  const loadArticles = async () => {
    setLoading(true)
    setError(null)
    setTraceId(null)
    
    try {
      const params: any = {}
      if (statusFilter) params.status = statusFilter
      if (featuredFilter !== "") params.featured = featuredFilter === "true"
      if (searchQuery) params.search = searchQuery
      
      const data = await articlesAdminApi.listArticles(params)
      setArticles(data)
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.message || "Failed to load articles")
      setTraceId(apiError.trace_id || null)
      if (apiError.code) {
        setError(`${apiError.code}: ${apiError.message}`)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleStatusAction = async (e: React.MouseEvent, articleId: string, action: 'publish' | 'archive') => {
    e.stopPropagation()
    try {
      if (action === 'publish') {
        await articlesAdminApi.publishArticle(articleId)
      } else if (action === 'archive') {
        await articlesAdminApi.archiveArticle(articleId)
      }
      loadArticles()
    } catch (err: any) {
      const apiError = parseApiError(err)
      setError(apiError.code ? `${apiError.code}: ${apiError.message}` : apiError.message || `Failed to ${action} article`)
      setTraceId(apiError.trace_id || null)
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

  if (loading && articles.length === 0) {
    return (
      <main className="container mx-auto p-8">
        <h1 className="text-3xl font-bold mb-6">Articles</h1>
        <p className="text-gray-500">Loading...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-8 max-w-7xl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Articles</h1>
        <Link
          href="/articles/new"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          New Article
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800 font-medium">{error}</div>
          {traceId && (
            <div className="text-xs text-red-600 font-mono mt-1">Trace ID: {traceId}</div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All</option>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="archived">Archived</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Featured</label>
            <select
              value={featuredFilter}
              onChange={(e) => setFeaturedFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All</option>
              <option value="true">Featured</option>
              <option value="false">Not Featured</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search title, subtitle, excerpt..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Articles table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Title</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Slug</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Featured</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Published</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {articles.map((article) => (
              <tr
                key={article.id}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => router.push(`/articles/${article.id}`)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{article.title}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-500">{article.slug}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusBadge(article.status)}`}>
                    {article.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {article.is_featured && (
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                      Featured
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDateTime(article.published_at)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDateTime(article.created_at)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <div className="flex gap-2">
                    {article.status === 'draft' && (
                      <button
                        onClick={(e) => handleStatusAction(e, article.id, 'publish')}
                        className="text-green-600 hover:text-green-900"
                      >
                        Publish
                      </button>
                    )}
                    {article.status === 'published' && (
                      <button
                        onClick={(e) => handleStatusAction(e, article.id, 'archive')}
                        className="text-red-600 hover:text-red-900"
                      >
                        Archive
                      </button>
                    )}
                    <Link
                      href={`/articles/${article.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      Edit
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {articles.length === 0 && !loading && (
          <div className="text-center py-12">
            <p className="text-gray-500">No articles found</p>
          </div>
        )}
      </div>
    </main>
  )
}

