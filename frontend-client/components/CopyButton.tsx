'use client'

import { useState } from 'react'

interface CopyButtonProps {
  value: string
  label?: string
  className?: string
}

export default function CopyButton({ value, label, className = '' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <code className="text-sm font-mono bg-gray-100 px-2 py-1 rounded flex-1 truncate">
        {label || value}
      </code>
      <button
        onClick={handleCopy}
        className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
      >
        {copied ? 'Copié' : 'Copier'}
      </button>
    </div>
  )
}

