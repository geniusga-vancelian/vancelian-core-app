/**
 * API configuration and utilities for admin frontend
 */

// Get API base URL - must be absolute for browser requests
// Import centralized config
import { getApiBaseUrl as getConfigApiBaseUrl } from './config'

export const getApiBaseUrl = (): string => {
  // Use centralized config (which handles fallbacks properly)
  return getConfigApiBaseUrl()
}

/**
 * Get the full API URL for an endpoint
 */
export const getApiUrl = (endpoint: string): string => {
  const baseUrl = getApiBaseUrl()
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
  return `${baseUrl}/${cleanEndpoint}`
}

/**
 * Get stored authentication token
 */
export const getToken = (): string | null => {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

/**
 * Store authentication token
 */
export const setToken = (token: string): void => {
  if (typeof window === 'undefined') return
  localStorage.setItem('access_token', token)
}

/**
 * Remove authentication token
 */
export const removeToken = (): void => {
  if (typeof window === 'undefined') return
  localStorage.removeItem('access_token')
  localStorage.removeItem('user_id')
}

/**
 * Generic API request helper with authentication
 */
export async function apiRequest<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = getApiUrl(endpoint)
  const token = getToken()

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options?.headers,
  }

  // DEV: Debug logging
  if (process.env.NODE_ENV === 'development') {
    console.log('[ADMIN API]', {
      baseUrl: getApiBaseUrl(),
      requestUrl: url,
      method: options?.method || 'GET',
      hasToken: !!token,
    })
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  // DEV: Debug response
  if (process.env.NODE_ENV === 'development') {
    console.log('[ADMIN API]', {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
    })
  }

  if (!response.ok) {
    let errorData: any = { message: `API request failed for ${endpoint}` }
    const contentType = response.headers.get('content-type') || ''
    
    try {
      if (contentType.includes('application/json')) {
        errorData = await response.json()
      } else {
        // Try to read as text for non-JSON responses
        const text = await response.text()
        if (text) {
          try {
            errorData = JSON.parse(text)
          } catch {
            errorData.message = text || response.statusText || errorData.message
          }
        } else {
          errorData.message = response.statusText || errorData.message
        }
      }
    } catch (e) {
      errorData.message = response.statusText || errorData.message
    }
    
    // Enhanced logging for 422 validation errors
    if (response.status === 422 && errorData.detail) {
      console.error('[ADMIN API] Validation Error (422):', {
        endpoint,
        url,
        status: response.status,
        detail: errorData.detail,
        // If detail is an array (Pydantic validation errors), format it nicely
        validationErrors: Array.isArray(errorData.detail)
          ? errorData.detail.map((err: any) => ({
              field: err.loc?.join('.') || 'unknown',
              message: err.msg || err.message || 'Validation error',
              type: err.type || 'unknown',
            }))
          : errorData.detail,
      })
    }
    
    throw {
      message: errorData.message || errorData.detail || `API request failed for ${endpoint}`,
      code: errorData.code,
      status: response.status,
      trace_id: errorData.trace_id,
      endpoint: endpoint,
      detail: errorData.detail, // Include full detail for validation errors
      validationErrors: Array.isArray(errorData.detail)
        ? errorData.detail.map((err: any) => ({
            field: err.loc?.join('.') || 'unknown',
            message: err.msg || err.message || 'Validation error',
            type: err.type || 'unknown',
          }))
        : undefined,
    }
  }

  return response.json()
}

/**
 * Parses an API error object for consistent display
 */
export function parseApiError(err: any): { 
  message: string
  code?: string
  status?: number
  trace_id?: string
  endpoint?: string
  validationErrors?: Array<{ field: string; message: string; type: string }>
} {
  if (typeof err === 'object' && err !== null) {
    return {
      message: err.message || "An unknown error occurred",
      code: err.code,
      status: err.status,
      trace_id: err.trace_id,
      endpoint: err.endpoint,
      validationErrors: err.validationErrors,
    }
  }
  return { message: String(err) }
}

/**
 * Types
 */
export type Offer = {
  id: string
  code: string
  name: string
  description?: string
  currency: string
  max_amount: string
  committed_amount: string
  remaining_amount: string
  maturity_date?: string
  status: 'DRAFT' | 'LIVE' | 'PAUSED' | 'CLOSED'
  metadata?: Record<string, any>
  created_at: string
  updated_at?: string
  // Marketing V1.1
  cover_media_id?: string
  promo_video_media_id?: string
  cover_url?: string
  location_label?: string
  location_lat?: string
  location_lng?: string
  marketing_title?: string
  marketing_subtitle?: string
  marketing_why?: Array<{ title: string; body: string }>
  marketing_highlights?: string[]
  marketing_breakdown?: { purchase_cost?: number; transaction_cost?: number; running_cost?: number }
  marketing_metrics?: { gross_yield?: number; net_yield?: number; annualised_return?: number; investors_count?: number; days_left?: number }
  fill_percentage?: number
}

export type CreateOfferPayload = {
  code: string
  name: string
  description?: string
  currency?: string
  max_amount: string
  maturity_date?: string
  metadata?: Record<string, any>
}

export type UpdateOfferPayload = {
  name?: string
  description?: string
  max_amount?: string
  maturity_date?: string
  metadata?: Record<string, any>
}

export type UpdateMarketingPayload = {
  cover_media_id?: string
  promo_video_media_id?: string
  location_label?: string
  location_lat?: number  // Normalized: number, not string
  location_lng?: number  // Normalized: number, not string
  marketing_title?: string
  marketing_subtitle?: string
  marketing_why?: Array<{ title: string; body: string }>
  marketing_highlights?: string[]
  marketing_breakdown?: { purchase_cost?: number; transaction_cost?: number; running_cost?: number }
  marketing_metrics?: { gross_yield?: number; net_yield?: number; annualised_return?: number; investors_count?: number; days_left?: number }
}

/**
 * Admin API
 */
export const adminApi = {
  /**
   * List users
   */
  listUsers: async (params?: { limit?: number; offset?: number }): Promise<Array<{
    user_id: string
    email: string
    first_name?: string
    last_name?: string
    status: string
    created_at: string
  }>> => {
    const limit = params?.limit || 200
    const offset = params?.offset || 0
    try {
      return await apiRequest<Array<{
        user_id: string
        email: string
        first_name?: string
        last_name?: string
        status: string
        created_at: string
      }>>(`admin/v1/users?limit=${limit}&offset=${offset}`)
    } catch (err: any) {
      // Enhanced error logging
      console.error('[Admin API] listUsers failed:', {
        error: err,
        status: err.status,
        code: err.code,
        trace_id: err.trace_id,
        hasToken: !!getToken(),
      })
      throw err
    }
  },

  /**
   * Resolve user by email
   */
  resolveUser: async (email: string): Promise<{
    user_id: string
    email: string
    found: boolean
  }> => {
    return apiRequest<{
      user_id: string
      email: string
      found: boolean
    }>('admin/v1/users/resolve', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  },
}

/**
 * Offers Admin API
 */
export const offersAdminApi = {
  listOffers: async (params?: { status?: string; currency?: string; limit?: number; offset?: number }): Promise<Offer[]> => {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    if (params?.currency) queryParams.append('currency', params.currency)
    if (params?.limit) queryParams.append('limit', String(params.limit))
    if (params?.offset) queryParams.append('offset', String(params.offset))
    const query = queryParams.toString()
    return apiRequest<Offer[]>(`admin/v1/offers${query ? `?${query}` : ''}`)
  },

  getOffer: async (offerId: string): Promise<Offer> => {
    return apiRequest<Offer>(`admin/v1/offers/${offerId}`)
  },

  createOffer: async (payload: CreateOfferPayload): Promise<Offer> => {
    return apiRequest<Offer>('admin/v1/offers', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  updateOffer: async (offerId: string, payload: UpdateOfferPayload): Promise<Offer> => {
    return apiRequest<Offer>(`admin/v1/offers/${offerId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  publishOffer: async (offerId: string): Promise<Offer> => {
    return apiRequest<Offer>(`admin/v1/offers/${offerId}/publish`, {
      method: 'POST',
    })
  },

  pauseOffer: async (offerId: string): Promise<Offer> => {
    return apiRequest<Offer>(`admin/v1/offers/${offerId}/pause`, {
      method: 'POST',
    })
  },

  closeOffer: async (offerId: string): Promise<Offer> => {
    return apiRequest<Offer>(`admin/v1/offers/${offerId}/close`, {
      method: 'POST',
    })
  },

  listOfferInvestments: async (offerId: string, params?: { status?: string; limit?: number; offset?: number }): Promise<{
    items: Array<{
      id: string
      user_email: string
      requested_amount: string
      allocated_amount: string
      status: string
      created_at: string
      idempotency_key?: string
    }>
    total: number
    limit: number
    offset: number
  }> => {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    if (params?.limit) queryParams.append('limit', String(params.limit))
    if (params?.offset) queryParams.append('offset', String(params.offset))
    const query = queryParams.toString()
    return apiRequest(`admin/v1/offers/${offerId}/investments${query ? `?${query}` : ''}`)
  },

  // Media endpoints
  presignUpload: async (offerId: string, payload: {
    upload_type: 'media' | 'document'
    file_name: string
    mime_type: string
    size_bytes: number
    media_type?: 'IMAGE' | 'VIDEO'
    document_kind?: string
  }): Promise<{ upload_url: string; key: string; required_headers: Record<string, string>; expires_in: number }> => {
    return apiRequest(`admin/v1/offers/${offerId}/uploads/presign`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  createOfferMedia: async (offerId: string, payload: {
    key: string
    mime_type: string
    size_bytes: number
    type: 'IMAGE' | 'VIDEO'
    sort_order?: number
    is_cover?: boolean
    visibility?: 'PUBLIC' | 'PRIVATE'
    url?: string
    width?: number
    height?: number
    duration_seconds?: number
  }): Promise<any> => {
    return apiRequest(`admin/v1/offers/${offerId}/media`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  listOfferMedia: async (offerId: string): Promise<Array<{
    id: string
    type: 'IMAGE' | 'VIDEO'
    url?: string
    mime_type: string
    size_bytes: number
    sort_order: number
    is_cover: boolean
    created_at: string
  }>> => {
    return apiRequest(`admin/v1/offers/${offerId}/media`)
  },

  reorderOfferMedia: async (offerId: string, items: Array<{ id: string; sort_order: number; is_cover?: boolean }>): Promise<void> => {
    return apiRequest(`admin/v1/offers/${offerId}/media/reorder`, {
      method: 'PATCH',
      body: JSON.stringify({ items }),
    })
  },

  deleteOfferMedia: async (offerId: string, mediaId: string): Promise<void> => {
    return apiRequest(`admin/v1/offers/${offerId}/media/${mediaId}`, {
      method: 'DELETE',
    })
  },

  // Documents endpoints
  createOfferDocument: async (offerId: string, payload: {
    name: string
    kind: string
    key: string
    mime_type: string
    size_bytes: number
    visibility?: 'PUBLIC' | 'PRIVATE'
    url?: string
  }): Promise<any> => {
    return apiRequest(`admin/v1/offers/${offerId}/documents`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  listOfferDocuments: async (offerId: string): Promise<Array<{
    id: string
    name: string
    kind: string
    url?: string
    mime_type: string
    size_bytes: number
    created_at: string
  }>> => {
    return apiRequest(`admin/v1/offers/${offerId}/documents`)
  },

  deleteOfferDocument: async (offerId: string, docId: string): Promise<void> => {
    return apiRequest(`admin/v1/offers/${offerId}/documents/${docId}`, {
      method: 'DELETE',
    })
  },

  // Marketing V1.1 endpoints
  updateOfferMarketing: async (offerId: string, payload: UpdateMarketingPayload): Promise<Offer> => {
    return apiRequest(`admin/v1/offers/${offerId}/marketing`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  seedOfferMarketingDefaults: async (offerId: string): Promise<Offer> => {
    return apiRequest(`admin/v1/offers/${offerId}/marketing/seed-defaults`, {
      method: 'POST',
    })
  },

  setCoverMedia: async (offerId: string, mediaId: string): Promise<Offer> => {
    return apiRequest(`admin/v1/offers/${offerId}/media/${mediaId}/set-cover`, {
      method: 'POST',
    })
  },

  setPromoVideo: async (offerId: string, mediaId: string): Promise<Offer> => {
    return apiRequest(`admin/v1/offers/${offerId}/media/${mediaId}/set-promo-video`, {
      method: 'POST',
    })
  },
}

/**
 * Articles Admin API
 */
export type Article = {
  id: string
  slug: string
  status: 'draft' | 'published' | 'archived'
  title: string
  subtitle?: string
  excerpt?: string
  content_markdown?: string
  content_html?: string
  cover_media_id?: string
  promo_video_media_id?: string
  author_name?: string
  published_at?: string
  created_at: string
  updated_at?: string
  seo_title?: string
  seo_description?: string
  tags: string[]
  is_featured: boolean
  allow_comments: boolean
  media: Array<{
    id: string
    type: 'image' | 'video' | 'document'
    key: string
    url?: string
    mime_type: string
    size_bytes: number
    width?: number
    height?: number
    duration_seconds?: number
    created_at: string
  }>
  offer_ids: string[]
}

export type ArticleListItem = {
  id: string
  slug: string
  title: string
  status: 'draft' | 'published' | 'archived'
  published_at?: string
  created_at: string
  updated_at?: string
  is_featured: boolean
}

export type CreateArticlePayload = {
  slug: string
  title: string
  subtitle?: string
  excerpt?: string
  content_markdown?: string
  author_name?: string
  seo_title?: string
  seo_description?: string
  tags?: string[]
  is_featured?: boolean
}

export type UpdateArticlePayload = {
  slug?: string
  title?: string
  subtitle?: string
  excerpt?: string
  content_markdown?: string
  content_html?: string
  author_name?: string
  seo_title?: string
  seo_description?: string
  tags?: string[]
  is_featured?: boolean
  status?: 'draft' | 'published' | 'archived'
}

export const articlesAdminApi = {
  listArticles: async (params?: {
    status?: string
    featured?: boolean
    offer_id?: string
    search?: string
    limit?: number
    offset?: number
  }): Promise<ArticleListItem[]> => {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    if (params?.featured !== undefined) queryParams.append('featured', String(params.featured))
    if (params?.offer_id) queryParams.append('offer_id', params.offer_id)
    if (params?.search) queryParams.append('search', params.search)
    if (params?.limit) queryParams.append('limit', String(params.limit))
    if (params?.offset) queryParams.append('offset', String(params.offset))
    const query = queryParams.toString()
    return apiRequest<ArticleListItem[]>(`admin/v1/articles${query ? `?${query}` : ''}`)
  },

  getArticle: async (articleId: string): Promise<Article> => {
    return apiRequest<Article>(`admin/v1/articles/${articleId}`)
  },

  createArticle: async (payload: CreateArticlePayload): Promise<Article> => {
    return apiRequest<Article>('admin/v1/articles', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  updateArticle: async (articleId: string, payload: UpdateArticlePayload): Promise<Article> => {
    return apiRequest<Article>(`admin/v1/articles/${articleId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  publishArticle: async (articleId: string): Promise<Article> => {
    return apiRequest<Article>(`admin/v1/articles/${articleId}/publish`, {
      method: 'POST',
    })
  },

  archiveArticle: async (articleId: string): Promise<Article> => {
    return apiRequest<Article>(`admin/v1/articles/${articleId}/archive`, {
      method: 'POST',
    })
  },

  linkArticleOffers: async (articleId: string, offerIds: string[]): Promise<Article> => {
    return apiRequest<Article>(`admin/v1/articles/${articleId}/offers`, {
      method: 'PUT',
      body: JSON.stringify({ offer_ids: offerIds }),
    })
  },

  // Media endpoints
  presignArticleUpload: async (articleId: string, payload: {
    upload_type: 'image' | 'video' | 'document'
    file_name: string
    mime_type: string
    size_bytes: number
  }): Promise<{ upload_url: string; key: string; required_headers: Record<string, string>; expires_in: number }> => {
    return apiRequest(`admin/v1/articles/${articleId}/uploads/presign`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  createArticleMedia: async (articleId: string, payload: {
    key: string
    mime_type: string
    size_bytes: number
    type: 'image' | 'video' | 'document'
    url?: string
    width?: number
    height?: number
    duration_seconds?: number
  }): Promise<any> => {
    return apiRequest(`admin/v1/articles/${articleId}/media`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  listArticleMedia: async (articleId: string): Promise<Array<{
    id: string
    type: 'image' | 'video' | 'document'
    key: string
    url?: string
    mime_type: string
    size_bytes: number
    width?: number
    height?: number
    duration_seconds?: number
    created_at: string
  }>> => {
    return apiRequest(`admin/v1/articles/${articleId}/media`)
  },

  deleteArticleMedia: async (articleId: string, mediaId: string): Promise<void> => {
    return apiRequest(`admin/v1/articles/${articleId}/media/${mediaId}`, {
      method: 'DELETE',
    })
  },

  setArticleCover: async (articleId: string, mediaId: string): Promise<any> => {
    return apiRequest(`admin/v1/articles/${articleId}/media/${mediaId}/set-cover`, {
      method: 'POST',
    })
  },

  setArticlePromoVideo: async (articleId: string, mediaId: string): Promise<any> => {
    return apiRequest(`admin/v1/articles/${articleId}/media/${mediaId}/set-promo-video`, {
      method: 'POST',
    })
  },
}

/**
 * System API
 */
export const systemApi = {
  getStorageInfo: async (): Promise<{ enabled: boolean; provider?: string; bucket?: string }> => {
    return apiRequest('admin/v1/system/storage')
  },
}

