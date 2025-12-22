"use client"

import { useState, useEffect } from "react"
import { articlesAdminApi, type ArticleListItem } from "@/lib/api"

interface ArticlePickerProps {
  selectedArticleId: string | null
  onSelect: (articleId: string | null) => void
  onClear: () => void
}

export function ArticlePicker({ selectedArticleId, onSelect, onClear }: ArticlePickerProps) {
  const [articles, setArticles] = useState<ArticleListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadArticles()
  }, [])

  const loadArticles = async () => {
    setLoading(true)
    setError(null)
    try {
      const results = await articlesAdminApi.listArticles({
        status: "published",
        limit: 100,
        search: searchQuery || undefined,
      })
      setArticles(results)
    } catch (err: any) {
      setError("Failed to load articles")
      console.error("Failed to load articles:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Debounce search
    const timer = setTimeout(() => {
      if (searchQuery !== "") {
        loadArticles()
      } else {
        loadArticles()
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  const selectedArticle = articles.find((a) => a.id === selectedArticleId)

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <input
          type="text"
          placeholder="Search articles..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
        />
        {selectedArticleId && (
          <button
            onClick={onClear}
            className="px-3 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 text-sm"
          >
            Clear
          </button>
        )}
      </div>

      {selectedArticle && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-2 text-sm">
          <span className="font-medium">Selected: </span>
          {selectedArticle.title}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-2 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="border border-gray-300 rounded-md max-h-60 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center text-gray-500 text-sm">Loading articles...</div>
        ) : articles.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">No articles found</div>
        ) : (
          <div className="divide-y divide-gray-200">
            {articles.map((article) => (
              <label
                key={article.id}
                className="flex items-center gap-3 p-3 hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="radio"
                  name="article"
                  checked={selectedArticleId === article.id}
                  onChange={() => onSelect(article.id)}
                  className="w-4 h-4 text-blue-600"
                />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-gray-900 truncate">
                    {article.title}
                  </div>
                  {article.published_at && (
                    <div className="text-xs text-gray-500">
                      {new Date(article.published_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

