"use client"

import { useState } from "react"
import type { PresignedMediaItem } from "@/lib/api"

interface OfferImageCarouselProps {
  media?: {
    cover: PresignedMediaItem | null
    gallery: PresignedMediaItem[]
  } | null
  offerName: string
}

export function OfferImageCarousel({ media, offerName }: OfferImageCarouselProps) {
  const [currentImageIndex, setCurrentImageIndex] = useState(0)

  // Build image list: cover first (if exists), then gallery
  const images: PresignedMediaItem[] = []
  if (media?.cover) {
    images.push(media.cover)
  }
  images.push(...(media?.gallery || []))

  if (images.length === 0) {
    return (
      <div className="w-full h-48 bg-gradient-to-br from-blue-100 to-purple-100 flex items-center justify-center">
        <span className="text-gray-400 text-sm">No image</span>
      </div>
    )
  }

  const currentImage = images[currentImageIndex]
  const currentImageUrl = currentImage?.url || null

  if (images.length === 1) {
    // Single image - no carousel needed
    return (
      <div className="w-full h-48 bg-gray-200 overflow-hidden">
        {currentImageUrl ? (
          <img
            src={currentImageUrl}
            alt={offerName}
            className="w-full h-full object-cover"
            onError={(e) => {
              console.error('Failed to load image:', currentImageUrl)
              e.currentTarget.style.display = 'none'
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-gray-400 text-sm">No image available</span>
          </div>
        )}
      </div>
    )
  }

  // Multiple images - show carousel
  return (
    <div className="w-full h-48 bg-gray-200 overflow-hidden relative group">
      {currentImageUrl ? (
        <img
          src={currentImageUrl}
          alt={`${offerName} - Image ${currentImageIndex + 1}`}
          className="w-full h-full object-cover"
          onError={(e) => {
            console.error('Failed to load image:', currentImageUrl)
            e.currentTarget.style.display = 'none'
          }}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center">
          <span className="text-gray-400 text-sm">Loading image...</span>
        </div>
      )}
      
      {/* Navigation arrows */}
      <button
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setCurrentImageIndex((prev) => (prev - 1 + images.length) % images.length)
        }}
        className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity z-10"
        aria-label="Previous image"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      
      <button
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setCurrentImageIndex((prev) => (prev + 1) % images.length)
        }}
        className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white rounded-full p-2 opacity-0 group-hover:opacity-100 transition-opacity z-10"
        aria-label="Next image"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
      
      {/* Dots indicator */}
      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1 z-10">
        {images.map((_, idx) => (
          <button
            key={idx}
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              setCurrentImageIndex(idx)
            }}
            className={`w-2 h-2 rounded-full transition-all ${
              idx === currentImageIndex ? 'bg-white' : 'bg-white/50'
            }`}
            aria-label={`Go to image ${idx + 1}`}
          />
        ))}
      </div>
    </div>
  )
}

