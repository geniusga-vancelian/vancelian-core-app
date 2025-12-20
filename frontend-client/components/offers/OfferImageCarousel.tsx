"use client"

import { useState, useEffect } from "react"
import { getApiUrl } from "@/lib/config"
import { getToken } from "@/lib/api"

interface OfferImageCarouselProps {
  images: Array<{ id: string; url: string | null; is_cover: boolean }>
  offerName: string
  offerId: string
}

export function OfferImageCarousel({ images, offerName, offerId }: OfferImageCarouselProps) {
  const [currentImageIndex, setCurrentImageIndex] = useState(0)
  const [imageUrls, setImageUrls] = useState<Record<string, string>>({})

  // Fetch presigned URLs for media without URLs
  useEffect(() => {
    const fetchPresignedUrls = async () => {
      const urls: Record<string, string> = {}
      
      // Fetch presigned URLs for images without URLs
      for (const image of images) {
        if (!image.url && image.id) {
          try {
            const token = getToken()
            const response = await fetch(
              getApiUrl(`api/v1/offers/${offerId}/media/${image.id}/download`),
              {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
              }
            )
            if (response.ok) {
              const data = await response.json()
              if (data.download_url) {
                urls[image.id] = data.download_url
              }
            }
          } catch (err) {
            console.warn(`Failed to fetch presigned URL for media ${image.id}:`, err)
          }
        } else if (image.url) {
          urls[image.id] = image.url
        }
      }
      
      setImageUrls(urls)
    }
    
    if (images.length > 0) {
      fetchPresignedUrls()
    }
  }, [images, offerId])

  if (images.length === 0) {
    return (
      <div className="w-full h-48 bg-gradient-to-br from-blue-100 to-purple-100 flex items-center justify-center">
        <span className="text-gray-400 text-sm">No image</span>
      </div>
    )
  }

  const currentImage = images[currentImageIndex]
  const currentImageUrl = currentImage ? (imageUrls[currentImage.id] || currentImage.url) : null

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
            <span className="text-gray-400 text-sm">Loading image...</span>
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

