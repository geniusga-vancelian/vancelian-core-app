"use client"

import type { PresignedDocumentItem } from "@/lib/api"

interface OfferDocumentsListProps {
  documents?: PresignedDocumentItem[]
}

export function OfferDocumentsList({ documents }: OfferDocumentsListProps) {
  if (!documents || documents.length === 0) {
    return null
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getDocumentIcon = (kind: string): string => {
    switch (kind) {
      case 'BROCHURE':
        return '📄'
      case 'MEMO':
        return '📝'
      case 'PROJECTIONS':
        return '📊'
      case 'VALUATION':
        return '💰'
      default:
        return '📎'
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">Documents</h3>
      <div className="space-y-3">
        {documents.map((doc) => (
          <a
            key={doc.id}
            href={doc.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-blue-300 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">{getDocumentIcon(doc.kind)}</span>
              <div>
                <div className="font-medium text-gray-900">{doc.name}</div>
                <div className="text-sm text-gray-500">
                  {doc.kind} • {formatFileSize(doc.size_bytes)}
                </div>
              </div>
            </div>
            <svg
              className="w-5 h-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        ))}
      </div>
    </div>
  )
}

