'use client'

import { formatDateTime } from '@/lib/format'

interface TimelineItem {
  label: string
  status: 'completed' | 'active' | 'pending' | 'failed'
  timestamp?: string | null
}

interface TimelineProps {
  items: TimelineItem[]
}

export default function Timeline({ items }: TimelineProps) {
  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={index} className="flex items-start gap-4">
          {/* Timeline dot */}
          <div className="flex flex-col items-center">
            <div
              className={`w-3 h-3 rounded-full ${
                item.status === 'completed'
                  ? 'bg-green-500'
                  : item.status === 'active'
                  ? 'bg-blue-500 ring-2 ring-blue-200'
                  : item.status === 'failed'
                  ? 'bg-red-500'
                  : 'bg-gray-300'
              }`}
            />
            {index < items.length - 1 && (
              <div
                className={`w-0.5 h-12 mt-1 ${
                  item.status === 'completed' ? 'bg-green-500' : 'bg-gray-300'
                }`}
              />
            )}
          </div>
          
          {/* Timeline content */}
          <div className="flex-1 pb-4">
            <div className="font-medium text-gray-900">{item.label}</div>
            {item.timestamp && (
              <div className="text-sm text-gray-500 mt-1">
                {formatDateTime(item.timestamp)}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

