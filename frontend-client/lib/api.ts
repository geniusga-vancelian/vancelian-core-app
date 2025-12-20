/**
 * API configuration and utilities
 */

import { getApiBaseUrl, getApiUrl } from './config'

// Re-export for backward compatibility
export { getApiBaseUrl, getApiUrl }

/**
 * Get stored authentication token
 */
export const getToken = (): string | null => {
  if (typeof window === 'undefined') return null
  return sessionStorage.getItem('dev_client_token')
}

/**
 * Store authentication token
 */
export const setToken = (token: string): void => {
  if (typeof window === 'undefined') return
  sessionStorage.setItem('dev_client_token', token)
}

/**
 * Remove authentication token
 */
export const removeToken = (): void => {
  if (typeof window === 'undefined') return
  sessionStorage.removeItem('dev_client_token')
}

/**
 * Make an authenticated API request
 */
export const apiRequest = async (
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> => {
  const token = getToken()
  const url = getApiUrl(endpoint)
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  return fetch(url, {
    ...options,
    headers,
  })
}

/**
 * Safely parse JSON from a Response, handling empty bodies (204 No Content, etc.)
 * Returns null if body is empty or not JSON, otherwise returns parsed JSON
 */
async function parseJsonSafe(res: Response): Promise<any | null> {
  // 204 No Content - no body expected
  if (res.status === 204) {
    return null
  }

  // Check content-length header if present
  const contentLength = res.headers.get('content-length')
  if (contentLength === '0') {
    return null
  }

  // Check content-type header
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    // Not JSON, try to read as text
    const text = await res.text()
    if (!text || text.trim().length === 0) {
      return null
    }
    // Try to parse as JSON anyway (some APIs don't set content-type correctly)
    try {
      return JSON.parse(text)
    } catch {
      return null
    }
  }

  // Read body as text first to check if empty
  const text = await res.text()
  if (!text || text.trim().length === 0) {
    return null
  }

  // Parse JSON
  try {
    return JSON.parse(text)
  } catch (e) {
    // If parsing fails, return null (don't throw - let caller handle)
    return null
  }
}

/**
 * Parse API error response
 */
export const parseApiError = async (response: Response): Promise<{
  code?: string
  message?: string
  trace_id?: string
  details?: any
}> => {
  const data = await parseJsonSafe(response)
  if (data !== null) {
    return {
      code: data.error?.code || data.code,
      message: data.error?.message || data.detail || data.message || 'Unknown error',
      trace_id: data.error?.trace_id || data.trace_id,
      details: data.error?.details || data.details,
    }
  }
  // Fallback if no JSON body
  return {
    message: `HTTP ${response.status}: ${response.statusText}`,
  }
}

/**
 * Offers API
 */
export interface MediaItem {
  id: string
  type: 'IMAGE' | 'VIDEO'
  url?: string | null
  mime_type: string
  size_bytes: number
  sort_order: number
  is_cover: boolean
  created_at: string
  width?: number
  height?: number
  duration_seconds?: number
}

export interface DocumentItem {
  id: string
  name: string
  kind: string
  url?: string | null
  mime_type: string
  size_bytes: number
  created_at: string
}

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
  media?: MediaItem[]
  documents?: DocumentItem[]
  // Marketing V1.1 fields
  cover_media_id?: string | null
  promo_video_media_id?: string | null
  cover_url?: string | null
  location_label?: string | null
  location_lat?: string | null
  location_lng?: string | null
  marketing_title?: string | null
  marketing_subtitle?: string | null
  marketing_why?: Array<{ title: string; body: string }> | null
  marketing_highlights?: string[] | null
  marketing_breakdown?: {
    purchase_cost?: number
    transaction_cost?: number
    running_cost?: number
  } | null
  marketing_metrics?: {
    gross_yield?: number
    net_yield?: number
    annualised_return?: number
    investors_count?: number
    days_left?: number
  } | null
  fill_percentage?: number
}

export interface ListOffersParams {
  status?: 'DRAFT' | 'LIVE' | 'PAUSED' | 'CLOSED'
  currency?: string
  limit?: number
  offset?: number
}

export interface InvestInOfferPayload {
  amount: string
  currency: string
  idempotency_key?: string
}

export interface InvestInOfferResponse {
  investment_id: string
  offer_id: string
  requested_amount: string
  accepted_amount: string
  currency: string
  status: string
  offer_committed_amount: string
  offer_remaining_amount: string
  created_at: string
}

export const offersApi = {
  /**
   * List offers
   */
  listOffers: async (params?: ListOffersParams): Promise<Offer[]> => {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    if (params?.currency) queryParams.append('currency', params.currency)
    queryParams.append('limit', String(params?.limit || 50))
    queryParams.append('offset', String(params?.offset || 0))
    
    const response = await apiRequest(`api/v1/offers?${queryParams.toString()}`)
    if (!response.ok) {
      const error = await parseApiError(response)
      const err: any = new Error(error.message || 'Failed to fetch offers')
      err.code = error.code
      err.trace_id = error.trace_id
      err.status = response.status
      throw err
    }
    return response.json()
  },

  /**
   * Get offer by ID
   */
  getOffer: async (id: string): Promise<Offer> => {
    const response = await apiRequest(`api/v1/offers/${id}`)
    if (!response.ok) {
      const error = await parseApiError(response)
      const err: any = new Error(error.message || 'Failed to fetch offer')
      err.code = error.code
      err.trace_id = error.trace_id
      err.status = response.status
      throw err
    }
    return response.json()
  },

  /**
   * Invest in an offer
   */
  invest: async (offerId: string, payload: InvestInOfferPayload): Promise<InvestInOfferResponse> => {
    const response = await apiRequest(`api/v1/offers/${offerId}/invest`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      const error = await parseApiError(response)
      const err: any = new Error(error.message || 'Failed to invest in offer')
      err.code = error.code
      err.trace_id = error.trace_id
      err.status = response.status
      throw err
    }
    return response.json()
  },
}

/**
 * Investments API
 */
export interface CreateInvestmentPayload {
  amount: string
  currency: string
  offer_id: string
  reason: string
}

export interface CreateInvestmentResponse {
  transaction_id: string
  status: string
}

export interface InvestmentPosition {
  investment_id: string
  offer_id: string
  offer_code: string
  offer_name: string
  principal: string
  currency: string
  status: string
  created_at: string
}

export interface ListInvestmentsParams {
  currency?: string
  status?: string
  limit?: number
}

export const investmentsApi = {
  /**
   * Create investment
   */
  create: async (payload: CreateInvestmentPayload): Promise<CreateInvestmentResponse> => {
    const response = await apiRequest('api/v1/investments', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      const error = await parseApiError(response)
      const err: any = new Error(error.message || 'Failed to create investment')
      err.code = error.code
      err.trace_id = error.trace_id
      err.status = response.status
      throw err
    }
    return response.json()
  },

  /**
   * List investment positions
   */
  list: async (params?: ListInvestmentsParams): Promise<InvestmentPosition[]> => {
    const queryParams = new URLSearchParams()
    if (params?.currency) queryParams.append('currency', params.currency)
    if (params?.status) queryParams.append('status', params.status)
    queryParams.append('limit', String(params?.limit || 50))
    
    const response = await apiRequest(`api/v1/investments?${queryParams.toString()}`)
    if (!response.ok) {
      const error = await parseApiError(response)
      const err: any = new Error(error.message || 'Failed to fetch investments')
      err.code = error.code
      err.trace_id = error.trace_id
      err.status = response.status
      throw err
    }
    return response.json()
  },
}

/**
 * Transactions API
 */
export interface Transaction {
  transaction_id?: string
  operation_id?: string
  type: string
  operation_type?: string
  status: string
  amount: string
  currency: string
  created_at: string
  metadata?: Record<string, any>
  offer_product?: string
}

export interface TransactionDetail {
  id: string
  type: string
  status: string
  amount: string
  currency: string
  created_at: string
  updated_at?: string | null
  metadata?: Record<string, any>
  trace_id?: string | null
  user_email?: string | null
  operation_id?: string | null
  operation_type?: string | null
  movement?: {
    from_bucket: string
    to_bucket: string
  } | null
}

export const transactionsApi = {
  /**
   * List transactions
   */
  list: async (currency?: string, limit?: number): Promise<Transaction[]> => {
    const queryParams = new URLSearchParams()
    if (currency) queryParams.append('currency', currency)
    queryParams.append('limit', String(limit || 50))
    
    const response = await apiRequest(`api/v1/transactions?${queryParams.toString()}`)
    if (!response.ok) {
      const error = await parseApiError(response)
      const err: any = new Error(error.message || 'Failed to fetch transactions')
      err.code = error.code
      err.trace_id = error.trace_id
      err.status = response.status
      throw err
    }
    return response.json()
  },

  /**
   * Get transaction by ID
   */
  getById: async (transactionId: string): Promise<TransactionDetail> => {
    const response = await apiRequest(`api/v1/transactions/${transactionId}`)
    if (!response.ok) {
      const error = await parseApiError(response)
      const err: any = new Error(error.message || 'Failed to fetch transaction')
      err.code = error.code
      err.trace_id = error.trace_id
      err.status = response.status
      throw err
    }
    return response.json()
  },
}

