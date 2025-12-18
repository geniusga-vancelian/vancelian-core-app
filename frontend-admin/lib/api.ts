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
    
    throw {
      message: errorData.message || errorData.detail || `API request failed for ${endpoint}`,
      code: errorData.code,
      status: response.status,
      trace_id: errorData.trace_id,
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

