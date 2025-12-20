"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { articlesApi, parseApiError, type ArticleListItem } from "@/lib/api"

export default function BlogPage() {
  const [articles, setArticles] = useState<ArticleListItem[]>([])
  const [featuredArticles, setFeaturedArticles] = useState<ArticleListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tagFilter, setTagFilter] = useState<string>("")
  const [allTags, setAllTags] = useState<string[]>([])

  useEffect(() => {
    loadArticles()
  }, [tagFilter])

  const loadArticles = async () => {
    setLoading(true)
    setError(null)

    try {
      // Load featured articles
      const featured = await articlesApi.listArticles({ featured: true, limit: 3 })
      setFeaturedArticles(featured)

      // Load all articles (with optional tag filter)
      const params: any = { limit: 50, offset: 0 }
      if (tagFilter) params.tag = tagFilter
      
      const all = await articlesApi.listArticles(params)
      setArticles(all)

      // Extract all unique tags
      const tags = new Set<string>()
      all.forEach(article => {
        article.tags.forEach(tag => tags.add(tag))
      })
      setAllTags(Array.from(tags).sort())
    } catch (err: any) {
      const apiError = err.status ? await parseApiError(err) : { message: err.message || 'Failed to load articles' }
      setError(apiError.message || 'Failed to load articles')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string | null | undefined): string => {
    if (!dateString) return ""
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    } catch {
      return ""
    }
  }

  if (loading && articles.length === 0) {
    return (
      <main className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-8">Blog</h1>
        <p className="text-gray-500">Loading articles...</p>
      </main>
    )
  }

  return (
    <main className="container mx-auto px-4 py-8 max-w-7xl">
      <h1 className="text-4xl font-bold mb-8">Blog</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      {/* Featured Hero Section */}
      {featuredArticles.length > 0 && (
        <div className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Featured</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {featuredArticles.map((article) => (
              <Link
                key={article.id}
                href={`/blog/${article.slug}`}
                className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
              >
                {article.cover_url && (
                  <img
                    src={article.cover_url}
                    alt={article.title}
                    className="w-full h-48 object-cover"
                  />
                )}
                <div className="p-6">
                  <h3 className="text-xl font-semibold mb-2 line-clamp-2">{article.title}</h3>
                  {article.subtitle && (
                    <p className="text-gray-600 text-sm mb-2 line-clamp-2">{article.subtitle}</p>
                  )}
                  {article.excerpt && (
                    <p className="text-gray-500 text-sm mb-4 line-clamp-3">{article.excerpt}</p>
                  )}
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    {article.author_name && <span>{article.author_name}</span>}
                    {article.published_at && <span>{formatDate(article.published_at)}</span>}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mb-8">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setTagFilter("")}
            className={`px-4 py-2 rounded-full text-sm ${
              tagFilter === ""
                ? "bg-blue-600 text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            All
          </button>
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setTagFilter(tag)}
              className={`px-4 py-2 rounded-full text-sm ${
                tagFilter === tag
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Articles Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {articles.map((article) => (
          <Link
            key={article.id}
            href={`/blog/${article.slug}`}
            className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow"
          >
            {article.cover_url && (
              <img
                src={article.cover_url}
                alt={article.title}
                className="w-full h-48 object-cover"
              />
            )}
            <div className="p-6">
              <h3 className="text-xl font-semibold mb-2 line-clamp-2">{article.title}</h3>
              {article.subtitle && (
                <p className="text-gray-600 text-sm mb-2 line-clamp-2">{article.subtitle}</p>
              )}
              {article.excerpt && (
                <p className="text-gray-500 text-sm mb-4 line-clamp-3">{article.excerpt}</p>
              )}
              <div className="flex items-center justify-between text-xs text-gray-500">
                {article.author_name && <span>{article.author_name}</span>}
                {article.published_at && <span>{formatDate(article.published_at)}</span>}
              </div>
              {article.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-3">
                  {article.tags.slice(0, 3).map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </Link>
        ))}
      </div>

      {articles.length === 0 && !loading && (
        <div className="text-center py-12">
          <p className="text-gray-500">No articles found</p>
        </div>
      )}
    </main>
  )
}

