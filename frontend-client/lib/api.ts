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

