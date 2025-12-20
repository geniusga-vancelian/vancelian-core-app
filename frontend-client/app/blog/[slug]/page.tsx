"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { articlesApi, parseApiError, type ArticleDetail } from "@/lib/api"

export default function ArticleDetailPage() {
  const params = useParams()
  const router = useRouter()
  const slug = params.slug as string

  const [article, setArticle] = useState<ArticleDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (slug) {
      loadArticle()
    }
  }, [slug])

  const loadArticle = async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await articlesApi.getArticleBySlug(slug)
      setArticle(data)
    } catch (err: any) {
      const apiError = err.status ? await parseApiError(err) : { message: err.message || 'Failed to load article' }
      setError(apiError.message || 'Failed to load article')
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

  // Simple markdown to HTML converter (basic implementation)
  const renderMarkdown = (markdown: string | null | undefined): string => {
    if (!markdown) return ""
    
    // Very basic markdown rendering (for V1)
    // In production, use a library like marked or react-markdown
    let html = markdown
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/gim, '<em>$1</em>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      .replace(/\n\n/gim, '</p><p>')
      .replace(/\n/gim, '<br />')
    
    return `<p>${html}</p>`
  }

  if (loading) {
    return (
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <p className="text-gray-500">Loading article...</p>
      </main>
    )
  }

  if (error || !article) {
    return (
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error || "Article not found"}</div>
        </div>
      </main>
    )
  }

  return (
    <main className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-6">
        <Link href="/blog" className="text-blue-600 hover:underline text-sm">
          ← Back to Blog
        </Link>
      </div>

      <article>
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-4xl font-bold mb-4">{article.title}</h1>
          {article.subtitle && (
            <p className="text-xl text-gray-600 mb-4">{article.subtitle}</p>
          )}
          
          <div className="flex items-center gap-4 text-sm text-gray-500 mb-6">
            {article.author_name && <span>By {article.author_name}</span>}
            {article.published_at && <span>{formatDate(article.published_at)}</span>}
          </div>

          {article.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-6">
              {article.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </header>

        {/* Cover Image */}
        {article.media?.cover && (
          <div className="mb-8">
            <img
              src={article.media.cover.url}
              alt={article.title}
              className="w-full h-96 object-cover rounded-lg"
            />
          </div>
        )}

        {/* Promo Video */}
        {article.media?.promo_video && (
          <div className="mb-8">
            <video
              src={article.media.promo_video.url}
              controls
              className="w-full rounded-lg"
            />
          </div>
        )}

        {/* Content */}
        <div className="prose max-w-none mb-8">
          {article.content_html ? (
            <div dangerouslySetInnerHTML={{ __html: article.content_html }} />
          ) : article.content_markdown ? (
            <div dangerouslySetInnerHTML={{ __html: renderMarkdown(article.content_markdown) }} />
          ) : (
            <p className="text-gray-500 italic">No content available.</p>
          )}
        </div>

        {/* Gallery */}
        {article.media?.gallery && article.media.gallery.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Gallery</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {article.media.gallery.map((item) => (
                <div key={item.id}>
                  {item.type === 'image' ? (
                    <img
                      src={item.url}
                      alt=""
                      className="w-full h-64 object-cover rounded-lg"
                    />
                  ) : (
                    <video
                      src={item.url}
                      controls
                      className="w-full h-64 object-cover rounded-lg"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Documents */}
        {article.media?.documents && article.media.documents.length > 0 && (
          <div className="mb-8">
            <h2 className="text-2xl font-semibold mb-4">Documents</h2>
            <div className="space-y-2">
              {article.media.documents.map((doc) => (
                <a
                  key={doc.id}
                  href={doc.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  <span className="text-gray-700">{doc.mime_type}</span>
                  <span className="text-blue-600 hover:underline">Download →</span>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Related Offers */}
        {article.offers && article.offers.length > 0 && (
          <div className="border-t border-gray-200 pt-8 mt-8">
            <h2 className="text-2xl font-semibold mb-4">Related Offers</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {article.offers.map((offer) => (
                <Link
                  key={offer.id}
                  href={`/offers/${offer.id}`}
                  className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  <h3 className="font-semibold text-lg">{offer.code}</h3>
                  <p className="text-gray-600">{offer.name}</p>
                </Link>
              ))}
            </div>
          </div>
        )}
      </article>
    </main>
  )
}

