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

/**
 * Get Strapi CMS base URL from environment variable
 * 
 * Dual-base-url support:
 * - Browser/public: NEXT_PUBLIC_STRAPI_URL (e.g., http://localhost:1337)
 * - Server/internal (SSR): STRAPI_INTERNAL_URL (e.g., http://cms-strapi:1337)
 * 
 * In development: Falls back to appropriate defaults
 * In production: NEXT_PUBLIC_STRAPI_URL MUST be set (STRAPI_INTERNAL_URL recommended for SSR)
 */
export const getStrapiBaseUrl = (): string => {
  // Browser/client-side: use public URL
  if (typeof window !== 'undefined') {
    const envUrl = process.env.NEXT_PUBLIC_STRAPI_URL || process.env.STRAPI_URL;
    
    if (envUrl) {
      // Ensure it's an absolute URL
      if (!envUrl.startsWith('http://') && !envUrl.startsWith('https://')) {
        return `http://${envUrl}`;
      }
      return envUrl;
    }
    
    // Fallback for browser
    const fallback = 'http://localhost:1337';
    if (process.env.NODE_ENV === 'development') {
      console.warn(
        '[config] NEXT_PUBLIC_STRAPI_URL not set, using fallback:',
        fallback,
        '\nSet NEXT_PUBLIC_STRAPI_URL in your environment.'
      );
    }
    return fallback;
  }
  
  // Server-side/SSR: use internal URL (Docker service name) or fallback to public
  const internalUrl = process.env.STRAPI_INTERNAL_URL;
  const publicUrl = process.env.NEXT_PUBLIC_STRAPI_URL || process.env.STRAPI_URL;
  
  if (internalUrl) {
    // Ensure it's an absolute URL
    if (!internalUrl.startsWith('http://') && !internalUrl.startsWith('https://')) {
      return `http://${internalUrl}`;
    }
    return internalUrl;
  }
  
  // Fallback to public URL if internal not set
  if (publicUrl) {
    // Ensure it's an absolute URL
    if (!publicUrl.startsWith('http://') && !publicUrl.startsWith('https://')) {
      return `http://${publicUrl}`;
    }
    return publicUrl;
  }
  
  // Development fallback: use Docker service name for SSR
  if (process.env.NODE_ENV === 'development' || process.env.NODE_ENV !== 'production') {
    const fallback = 'http://cms-strapi:1337';
    console.warn(
      '[config] STRAPI_INTERNAL_URL not set for SSR, using fallback:',
      fallback,
      '\nSet STRAPI_INTERNAL_URL for Docker environments.'
    );
    return fallback;
  }
  
  // Production: fail if not set
  throw new Error('NEXT_PUBLIC_STRAPI_URL (and STRAPI_INTERNAL_URL for SSR) must be set in production');
};

/**
 * Get the full Strapi API URL for an endpoint
 */
export const getStrapiApiUrl = (endpoint: string): string => {
  const baseUrl = getStrapiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  // Ensure we use /api prefix for Strapi API
  const apiEndpoint = cleanEndpoint.startsWith('api/') ? cleanEndpoint : `api/${cleanEndpoint}`;
  return `${baseUrl}/${apiEndpoint}`;
};

