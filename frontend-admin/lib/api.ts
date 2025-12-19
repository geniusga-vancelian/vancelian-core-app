/**
 * API configuration and utilities for admin frontend
 */

// Get API base URL - must be absolute for browser requests
export const getApiBaseUrl = (): string => {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
  }
  
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
  
  if (!baseUrl.startsWith('http://') && !baseUrl.startsWith('https://')) {
    return `http://${baseUrl}`
  }
  
  return baseUrl
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
    try {
      errorData = await response.json()
    } catch (e) {
      errorData.message = response.statusText || errorData.message
    }
    
    // Backend returns {error: {code, message, trace_id}}, extract nested error object
    const error = errorData.error || errorData
    const message = error.message || error.detail || errorData.message || `API request failed for ${endpoint}`
    const code = error.code || errorData.code
    const trace_id = error.trace_id || errorData.trace_id
    
    throw {
      message,
      code,
      status: response.status,
      trace_id,
      endpoint: endpoint,
    }
  }

  return response.json()
}

/**
 * Parses an API error object for consistent display
 */
export function parseApiError(err: any): { message: string; code?: string; status?: number; trace_id?: string; endpoint?: string } {
  if (typeof err === 'object' && err !== null) {
    return {
      message: err.message || "An unknown error occurred",
      code: err.code,
      status: err.status,
      trace_id: err.trace_id,
      endpoint: err.endpoint,
    }
  }
  return { message: String(err) }
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
export interface Offer {
  id: string
  code: string
  name: string
  description?: string
  currency: string
  status: 'DRAFT' | 'LIVE' | 'PAUSED' | 'CLOSED'
  max_amount: string
  committed_amount: string
  remaining_amount: string
  maturity_date?: string
  metadata?: Record<string, any>
  created_at: string
  updated_at?: string
}

export interface CreateOfferPayload {
  code: string
  name: string
  description?: string
  currency?: string
  max_amount: string
  maturity_date?: string
  metadata?: Record<string, any>
}

export interface UpdateOfferPayload {
  name?: string
  description?: string
  max_amount?: string
  maturity_date?: string
  metadata?: Record<string, any>
}

export interface ListOffersParams {
  status?: 'DRAFT' | 'LIVE' | 'PAUSED' | 'CLOSED'
  currency?: string
  limit?: number
  offset?: number
}

export const offersAdminApi = {
  /**
   * List offers
   */
  listOffers: async (params?: ListOffersParams): Promise<Offer[]> => {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    if (params?.currency) queryParams.append('currency', params.currency)
    queryParams.append('limit', String(params?.limit || 50))
    queryParams.append('offset', String(params?.offset || 0))
    
    return apiRequest<Offer[]>(`admin/v1/offers?${queryParams.toString()}`)
  },

  /**
   * Create offer
   */
  createOffer: async (payload: CreateOfferPayload): Promise<Offer> => {
    return apiRequest<Offer>('admin/v1/offers', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Get offer by ID
   */
  getOffer: async (id: string): Promise<Offer> => {
    return apiRequest<Offer>(`admin/v1/offers/${id}`)
  },

  /**
   * Update offer
   */
  updateOffer: async (id: string, payload: UpdateOfferPayload): Promise<Offer> => {
    return apiRequest<Offer>(`admin/v1/offers/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Publish offer (DRAFT -> LIVE)
   */
  publishOffer: async (id: string): Promise<Offer> => {
    return apiRequest<Offer>(`admin/v1/offers/${id}/publish`, {
      method: 'POST',
    })
  },

  /**
   * Pause offer (LIVE -> PAUSED)
   */
  pauseOffer: async (id: string): Promise<Offer> => {
    return apiRequest<Offer>(`admin/v1/offers/${id}/pause`, {
      method: 'POST',
    })
  },

  /**
   * Close offer (LIVE/PAUSED -> CLOSED)
   */
  closeOffer: async (id: string): Promise<Offer> => {
    return apiRequest<Offer>(`admin/v1/offers/${id}/close`, {
      method: 'POST',
    })
  },

  /**
   * List investments for an offer (paginated)
   */
  listOfferInvestments: async (
    offerId: string,
    params?: { limit?: number; offset?: number; status?: 'ALL' | 'PENDING' | 'CONFIRMED' | 'REJECTED' }
  ): Promise<{
    items: Array<{
      id: string
      offer_id: string
      user_id: string
      user_email: string
      requested_amount: string
      allocated_amount: string
      currency: string
      status: 'PENDING' | 'CONFIRMED' | 'REJECTED'
      created_at: string
      updated_at?: string
      idempotency_key?: string
    }>
    limit: number
    offset: number
    total: number
  }> => {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    queryParams.append('limit', String(params?.limit || 50))
    queryParams.append('offset', String(params?.offset || 0))
    
    return apiRequest<{
      items: Array<{
        id: string
        offer_id: string
        user_id: string
        user_email: string
        requested_amount: string
        allocated_amount: string
        currency: string
        status: 'PENDING' | 'CONFIRMED' | 'REJECTED'
        created_at: string
        updated_at?: string
        idempotency_key?: string
      }>
      limit: number
      offset: number
      total: number
    }>(`admin/v1/offers/${offerId}/investments?${queryParams.toString()}`)
  },

  /**
   * Presign upload URL for media or document
   */
  presignUpload: async (
    offerId: string,
    payload: {
      upload_type: 'media' | 'document'
      file_name: string
      mime_type: string
      size_bytes: number
      media_type?: 'IMAGE' | 'VIDEO'
      document_kind?: 'BROCHURE' | 'MEMO' | 'PROJECTIONS' | 'VALUATION' | 'OTHER'
    }
  ): Promise<{
    upload_url: string
    key: string
    required_headers: Record<string, string>
    expires_in: number
  }> => {
    return apiRequest<{
      upload_url: string
      key: string
      required_headers: Record<string, string>
      expires_in: number
    }>(`admin/v1/offers/${offerId}/uploads/presign`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Create media metadata after upload
   */
  createOfferMedia: async (
    offerId: string,
    payload: {
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
    }
  ): Promise<{
    id: string
    offer_id: string
    type: string
    url?: string
    mime_type: string
    size_bytes: number
    sort_order: number
    is_cover: boolean
    created_at: string
    width?: number
    height?: number
    duration_seconds?: number
  }> => {
    return apiRequest<{
      id: string
      offer_id: string
      type: string
      url?: string
      mime_type: string
      size_bytes: number
      sort_order: number
      is_cover: boolean
      created_at: string
      width?: number
      height?: number
      duration_seconds?: number
    }>(`admin/v1/offers/${offerId}/media`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Create document metadata after upload
   */
  createOfferDocument: async (
    offerId: string,
    payload: {
      name: string
      kind: 'BROCHURE' | 'MEMO' | 'PROJECTIONS' | 'VALUATION' | 'OTHER'
      key: string
      mime_type: string
      size_bytes: number
      visibility?: 'PUBLIC' | 'PRIVATE'
      url?: string
    }
  ): Promise<{
    id: string
    offer_id: string
    name: string
    kind: string
    url?: string
    mime_type: string
    size_bytes: number
    created_at: string
  }> => {
    return apiRequest<{
      id: string
      offer_id: string
      name: string
      kind: string
      url?: string
      mime_type: string
      size_bytes: number
      created_at: string
    }>(`admin/v1/offers/${offerId}/documents`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /**
   * List media for an offer
   */
  listOfferMedia: async (offerId: string): Promise<Array<{
    id: string
    offer_id: string
    type: 'IMAGE' | 'VIDEO'
    url?: string
    mime_type: string
    size_bytes: number
    sort_order: number
    is_cover: boolean
    created_at: string
    width?: number
    height?: number
    duration_seconds?: number
  }>> => {
    return apiRequest<Array<{
      id: string
      offer_id: string
      type: 'IMAGE' | 'VIDEO'
      url?: string
      mime_type: string
      size_bytes: number
      sort_order: number
      is_cover: boolean
      created_at: string
      width?: number
      height?: number
      duration_seconds?: number
    }>>(`admin/v1/offers/${offerId}/media`)
  },

  /**
   * List documents for an offer
   */
  listOfferDocuments: async (offerId: string): Promise<Array<{
    id: string
    offer_id: string
    name: string
    kind: string
    url?: string
    mime_type: string
    size_bytes: number
    created_at: string
  }>> => {
    return apiRequest<Array<{
      id: string
      offer_id: string
      name: string
      kind: string
      url?: string
      mime_type: string
      size_bytes: number
      created_at: string
    }>>(`admin/v1/offers/${offerId}/documents`)
  },

  /**
   * Reorder media items
   */
  reorderOfferMedia: async (
    offerId: string,
    items: Array<{ id: string; sort_order: number; is_cover?: boolean }>
  ): Promise<void> => {
    return apiRequest<void>(`admin/v1/offers/${offerId}/media/reorder`, {
      method: 'PATCH',
      body: JSON.stringify({ items }),
    })
  },

  /**
   * Delete media item
   */
  deleteOfferMedia: async (offerId: string, mediaId: string): Promise<void> => {
    return apiRequest<void>(`admin/v1/offers/${offerId}/media/${mediaId}`, {
      method: 'DELETE',
    })
  },

  /**
   * Delete document
   */
  deleteOfferDocument: async (offerId: string, docId: string): Promise<void> => {
    return apiRequest<void>(`admin/v1/offers/${offerId}/documents/${docId}`, {
      method: 'DELETE',
    })
  },
}

