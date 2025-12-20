/**
 * Centralized configuration for frontend-client
 * All environment variables and defaults are defined here
 */

/**
 * Get API base URL from environment variable
 * 
 * In development: Falls back to http://localhost:8000 with a console warning
 * In production: NEXT_PUBLIC_API_BASE_URL MUST be set
 */
export const getApiBaseUrl = (): string => {
  const envUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  
  if (envUrl) {
    // Ensure it's an absolute URL
    if (!envUrl.startsWith('http://') && !envUrl.startsWith('https://')) {
      return `http://${envUrl}`;
    }
    return envUrl;
  }
  
  // Fallback only in development
  if (process.env.NODE_ENV === 'development' || process.env.NODE_ENV !== 'production') {
    const fallback = 'http://localhost:8000';
    if (typeof window !== 'undefined') {
      console.warn(
        '[config] NEXT_PUBLIC_API_BASE_URL not set, using fallback:',
        fallback,
        '\nSet NEXT_PUBLIC_API_BASE_URL in your environment.'
      );
    }
    return fallback;
  }
  
  // Production: fail if not set
  throw new Error('NEXT_PUBLIC_API_BASE_URL must be set in production');
};

/**
 * Get the full API URL for an endpoint
 */
export const getApiUrl = (endpoint: string): string => {
  const baseUrl = getApiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  return `${baseUrl}/${cleanEndpoint}`;
};

