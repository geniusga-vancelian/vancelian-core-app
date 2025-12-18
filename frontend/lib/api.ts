/**
 * API client for Vancelian Core Backend
 * DEV-ONLY: No production error handling or retries
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

export interface ApiError {
  code: string
  message: string
  details?: any
  trace_id?: string
}

export interface StandardErrorResponse {
  error: ApiError
}

/**
 * Get JWT token from sessionStorage (dev-only)
 */
function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return sessionStorage.getItem('dev_jwt_token')
}

/**
 * Make API request with authentication
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  const contentType = response.headers.get('content-type')
  const isJson = contentType?.includes('application/json')
  
  const data = isJson ? await response.json() : await response.text()
  const traceId = response.headers.get('X-Trace-ID')

  if (!response.ok) {
    const error: ApiError = {
      code: isJson && data.error?.code ? data.error.code : `HTTP_${response.status}`,
      message: isJson && data.error?.message ? data.error.message : data || response.statusText,
      details: isJson && data.error?.details ? data.error.details : undefined,
      trace_id: traceId || (isJson && data.error?.trace_id ? data.error.trace_id : undefined),
    }
    throw error
  }

  return data as T
}

/**
 * Wallet API
 */
export const walletApi = {
  getBalance: async (currency: string = 'AED') => {
    return apiRequest<{
      currency: string
      total_balance: string
      available_balance: string
      blocked_balance: string
      locked_balance: string
    }>(`/api/v1/wallet?currency=${currency}`)
  },
}

/**
 * Transactions API
 */
export const transactionsApi = {
  list: async (type?: string, status?: string, limit: number = 20) => {
    const params = new URLSearchParams()
    if (type) params.append('type', type)
    if (status) params.append('status', status)
    params.append('limit', limit.toString())
    
    return apiRequest<Array<{
      transaction_id: string
      type: string
      status: string
      amount: string
      currency: string
      created_at: string
    }>>(`/api/v1/transactions?${params.toString()}`)
  },
}

/**
 * Investments API
 */
export const investmentsApi = {
  create: async (data: {
    amount: string
    currency: string
    offer_id: string
    reason: string
  }) => {
    return apiRequest<{
      transaction_id: string
      status: string
    }>('/api/v1/investments', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
}

/**
 * Admin Compliance API
 */
export const complianceApi = {
  releaseFunds: async (data: {
    transaction_id: string
    amount: string
    reason: string
  }) => {
    return apiRequest<{
      transaction_id: string
      status: string
    }>('/admin/v1/compliance/release-funds', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  
  rejectDeposit: async (data: {
    transaction_id: string
    reason: string
  }) => {
    return apiRequest<{
      transaction_id: string
      status: string
    }>('/admin/v1/compliance/reject-deposit', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
}

/**
 * Webhooks API (dev tools)
 */
export const webhooksApi = {
  zandDeposit: async (data: {
    provider_event_id: string
    iban: string
    user_id: string
    amount: string
    currency: string
    occurred_at: string
  }, signature: string, timestamp?: string) => {
    const headers: HeadersInit = {
      'X-Zand-Signature': signature,
    }
    if (timestamp) {
      headers['X-Zand-Timestamp'] = timestamp
    }

    const response = await fetch(`${API_BASE_URL}/webhooks/v1/zand/deposit`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    })

    const traceId = response.headers.get('X-Trace-ID')
    const responseData = await response.json()

    if (!response.ok) {
      const error: ApiError = {
        code: responseData.error?.code || `HTTP_${response.status}`,
        message: responseData.error?.message || response.statusText,
        details: responseData.error?.details,
        trace_id: traceId || responseData.error?.trace_id,
      }
      throw error
    }

    return {
      ...responseData,
      trace_id: traceId,
    }
  },
}

