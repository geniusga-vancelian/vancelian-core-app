/**
 * Marketing payload normalizer
 * Converts form values (which may be empty strings) to backend-expected types
 */

/**
 * Convert empty string to undefined for optional string fields
 */
export function toOptString(v: string | undefined | null): string | undefined {
  if (v === null || v === undefined) return undefined
  const trimmed = String(v).trim()
  return trimmed === "" ? undefined : trimmed
}

/**
 * Convert string to number, or undefined if empty/invalid
 */
export function toOptFloat(v: string | number | undefined | null): number | undefined {
  if (v === null || v === undefined) return undefined
  if (typeof v === 'number') {
    return isFinite(v) ? v : undefined
  }
  const str = String(v).trim()
  if (str === "") return undefined
  const num = parseFloat(str)
  return isFinite(num) ? num : undefined
}

/**
 * Convert string to integer, or undefined if empty/invalid
 */
export function toOptInt(v: string | number | undefined | null): number | undefined {
  if (v === null || v === undefined) return undefined
  if (typeof v === 'number') {
    return Number.isInteger(v) ? v : undefined
  }
  const str = String(v).trim()
  if (str === "") return undefined
  const num = parseInt(str, 10)
  return isFinite(num) && Number.isInteger(num) ? num : undefined
}

/**
 * Clean array: remove empty strings, trim, dedupe
 */
export function cleanArray(arr: string[] | undefined | null): string[] | undefined {
  if (!arr || arr.length === 0) return undefined
  const cleaned = arr
    .map(item => String(item).trim())
    .filter(item => item.length > 0)
  return cleaned.length > 0 ? [...new Set(cleaned)] : undefined
}

/**
 * Clean why invest items: keep only items with title OR body, trim both
 */
export function cleanWhyInvest(
  items: Array<{ title: string; body: string }> | undefined | null
): Array<{ title: string; body: string }> | undefined {
  if (!items || items.length === 0) return undefined
  const cleaned = items
    .map(item => ({
      title: String(item.title || "").trim(),
      body: String(item.body || "").trim(),
    }))
    .filter(item => item.title.length > 0 || item.body.length > 0)
  return cleaned.length > 0 ? cleaned : undefined
}

/**
 * Normalize marketing form payload for backend
 * Removes empty strings, converts types, omits undefined fields
 */
export interface MarketingFormState {
  marketing_title?: string
  marketing_subtitle?: string
  location_label?: string
  location_lat?: string
  location_lng?: string
  marketing_why?: Array<{ title: string; body: string }>
  marketing_highlights?: string[]
  marketing_breakdown?: {
    purchase_cost?: number | string
    transaction_cost?: number | string
    running_cost?: number | string
  }
  marketing_metrics?: {
    gross_yield?: number | string
    net_yield?: number | string
    annualised_return?: number | string
    investors_count?: number | string
    days_left?: number | string
  }
}

export interface NormalizedMarketingPayload {
  marketing_title?: string
  marketing_subtitle?: string
  location_label?: string
  location_lat?: number
  location_lng?: number
  marketing_why?: Array<{ title: string; body: string }>
  marketing_highlights?: string[]
  marketing_breakdown?: {
    purchase_cost?: number
    transaction_cost?: number
    running_cost?: number
  }
  marketing_metrics?: {
    gross_yield?: number
    net_yield?: number
    annualised_return?: number
    investors_count?: number
    days_left?: number
  }
}

export function normalizeMarketingPayload(
  form: MarketingFormState
): NormalizedMarketingPayload {
  const payload: NormalizedMarketingPayload = {}

  // String fields
  const title = toOptString(form.marketing_title)
  if (title !== undefined) payload.marketing_title = title

  const subtitle = toOptString(form.marketing_subtitle)
  if (subtitle !== undefined) payload.marketing_subtitle = subtitle

  const locationLabel = toOptString(form.location_label)
  if (locationLabel !== undefined) payload.location_label = locationLabel

  // Numeric fields (lat/lng)
  const lat = toOptFloat(form.location_lat)
  if (lat !== undefined) payload.location_lat = lat

  const lng = toOptFloat(form.location_lng)
  if (lng !== undefined) payload.location_lng = lng

  // Why invest array
  const why = cleanWhyInvest(form.marketing_why)
  if (why !== undefined) payload.marketing_why = why

  // Highlights array
  const highlights = cleanArray(form.marketing_highlights)
  if (highlights !== undefined) payload.marketing_highlights = highlights

  // Breakdown object
  if (form.marketing_breakdown) {
    const breakdown: {
      purchase_cost?: number
      transaction_cost?: number
      running_cost?: number
    } = {}

    const purchaseCost = toOptFloat(form.marketing_breakdown.purchase_cost)
    if (purchaseCost !== undefined) breakdown.purchase_cost = purchaseCost

    const transactionCost = toOptFloat(form.marketing_breakdown.transaction_cost)
    if (transactionCost !== undefined) breakdown.transaction_cost = transactionCost

    const runningCost = toOptFloat(form.marketing_breakdown.running_cost)
    if (runningCost !== undefined) breakdown.running_cost = runningCost

    // Only include breakdown if at least one field is set
    if (Object.keys(breakdown).length > 0) {
      payload.marketing_breakdown = breakdown
    }
  }

  // Metrics object
  if (form.marketing_metrics) {
    const metrics: {
      gross_yield?: number
      net_yield?: number
      annualised_return?: number
      investors_count?: number
      days_left?: number
    } = {}

    const grossYield = toOptFloat(form.marketing_metrics.gross_yield)
    if (grossYield !== undefined) metrics.gross_yield = grossYield

    const netYield = toOptFloat(form.marketing_metrics.net_yield)
    if (netYield !== undefined) metrics.net_yield = netYield

    const annualisedReturn = toOptFloat(form.marketing_metrics.annualised_return)
    if (annualisedReturn !== undefined) metrics.annualised_return = annualisedReturn

    const investorsCount = toOptInt(form.marketing_metrics.investors_count)
    if (investorsCount !== undefined) metrics.investors_count = investorsCount

    const daysLeft = toOptInt(form.marketing_metrics.days_left)
    if (daysLeft !== undefined) metrics.days_left = daysLeft

    // Only include metrics if at least one field is set
    if (Object.keys(metrics).length > 0) {
      payload.marketing_metrics = metrics
    }
  }

  return payload
}

