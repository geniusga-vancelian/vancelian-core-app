/**
 * Date/time formatting helpers
 * Safe date parsing and formatting (never shows "Invalid Date")
 */

export function parseISODate(dateString: string | null | undefined): Date | null {
  if (!dateString) return null
  
  let normalized = dateString.trim()
  if (!normalized.includes('T')) {
    normalized = normalized + 'T00:00:00Z'
  } else if (!normalized.endsWith('Z') && !normalized.includes('+') && !normalized.includes('-', 10)) {
    normalized = normalized + 'Z'
  }
  
  try {
    const date = new Date(normalized)
    if (isNaN(date.getTime())) {
      return null
    }
    return date
  } catch {
    return null
  }
}

export function formatDateTime(dateString: string | null | undefined): string {
  const date = parseISODate(dateString)
  if (!date) {
    return "—"
  }
  
  return date.toLocaleString('fr-FR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'UTC',
  })
}

export function formatDate(dateString: string | null | undefined): string {
  const date = parseISODate(dateString)
  if (!date) {
    return "—"
  }
  
  return date.toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: 'UTC',
  })
}

export function formatRelativeTime(dateString: string | null | undefined): string {
  const date = parseISODate(dateString)
  if (!date) {
    return ""
  }
  
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)
  
  if (diffSeconds < 60) {
    return `il y a ${diffSeconds}s`
  } else if (diffMinutes < 60) {
    return `il y a ${diffMinutes}min`
  } else if (diffHours < 24) {
    return `il y a ${diffHours}h`
  } else if (diffDays < 7) {
    return `il y a ${diffDays}j`
  } else {
    return formatDate(dateString)
  }
}

