/**
 * API configuration and utilities
 */

// Get API base URL - must be absolute for browser requests
// Defaults to http://localhost:8000 (not docker service name)
export const getApiBaseUrl = (): string => {
  if (typeof window === 'undefined') {
    // Server-side: use environment variable or default
    return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
  }
  
  // Client-side: use environment variable or default to localhost
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
  
  // Ensure it's an absolute URL (not relative, not docker service name)
  if (!baseUrl.startsWith('http://') && !baseUrl.startsWith('https://')) {
    return `http://${baseUrl}`
  }
  
  // DEV: Log base URL
  if (process.env.NODE_ENV === 'development') {
    console.log('[api] baseUrl=', baseUrl)
  }
  
  return baseUrl
}

/**
 * Get the full API URL for an endpoint
 */
export const getApiUrl = (endpoint: string): string => {
  const baseUrl = getApiBaseUrl()
  // Remove leading slash from endpoint if present
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
  return `${baseUrl}/${cleanEndpoint}`
}

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
 * Parse API error response
 */
export const parseApiError = async (response: Response): Promise<{
  code?: string
  message?: string
  trace_id?: string
  details?: any
}> => {
  try {
    const data = await response.json()
    return {
      code: data.error?.code || data.code,
      message: data.error?.message || data.detail || data.message || 'Unknown error',
      trace_id: data.error?.trace_id || data.trace_id,
      details: data.error?.details || data.details,
    }
  } catch {
    return {
      message: `HTTP ${response.status}: ${response.statusText}`,
    }
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

