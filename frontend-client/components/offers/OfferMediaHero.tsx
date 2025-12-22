"use client"

import { useState } from "react"
import type { OfferMediaGroup } from "@/lib/api"

interface OfferMediaHeroProps {
  offerName: string
  media?: OfferMediaGroup | null
}

export function OfferMediaHero({ offerName, media }: OfferMediaHeroProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showGallery, setShowGallery] = useState(false)
  const [showVideoModal, setShowVideoModal] = useState(false)

  // Build image list: cover first (if exists), then gallery
  const images: Array<{ id: string; url: string }> = []
  if (media?.cover) {
    images.push({ id: media.cover.id, url: media.cover.url })
  }
  images.push(...(media?.gallery.map(m => ({ id: m.id, url: m.url })) || []))

  const currentImage = images[currentIndex] || null
  const currentImageUrl = currentImage?.url || null
  const promoVideo = media?.promo_video

  if (images.length === 0 && !promoVideo) {
    return (
      <div className="relative w-full h-96 bg-gradient-to-br from-gray-100 to-gray-200 rounded-lg flex items-center justify-center mb-6">
        <div className="text-center">
          <div className="text-4xl mb-2">📷</div>
          <p className="text-gray-500">No media uploaded yet</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="relative w-full h-96 bg-gray-200 rounded-lg overflow-hidden mb-6">
        {currentImageUrl ? (
          <>
            <img
              src={currentImageUrl}
              alt={`${offerName} - Image ${currentIndex + 1}`}
              className="w-full h-full object-cover"
              onError={(e) => {
                console.error('Failed to load image:', currentImageUrl)
                e.currentTarget.style.display = 'none'
              }}
            />
            {images.length > 1 && (
              <>
                <button
                  onClick={() => setCurrentIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1))}
                  className="absolute left-4 top-1/2 -translate-y-1/2 bg-black/50 text-white p-3 rounded-full hover:bg-black/70 transition-colors"
                  aria-label="Previous image"
                >
                  ←
                </button>
                <button
                  onClick={() => setCurrentIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0))}
                  className="absolute right-4 top-1/2 -translate-y-1/2 bg-black/50 text-white p-3 rounded-full hover:bg-black/70 transition-colors"
                  aria-label="Next image"
                >
                  →
                </button>
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
                  {images.map((_, idx) => (
                    <button
                      key={idx}
                      onClick={() => setCurrentIndex(idx)}
                      className={`w-2 h-2 rounded-full transition-colors ${
                        idx === currentIndex ? 'bg-white' : 'bg-white/50'
                      }`}
                      aria-label={`Go to image ${idx + 1}`}
                    />
                  ))}
                </div>
                <button
                  onClick={() => setShowGallery(true)}
                  className="absolute top-4 right-4 bg-white/90 text-gray-800 px-4 py-2 rounded-lg hover:bg-white font-medium text-sm shadow-lg"
                >
                  📷 Gallery
                </button>
              </>
            )}
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-gray-400">No image available</span>
          </div>
        )}
      </div>

      {/* Promo Video Button */}
      {promoVideo && (
        <div className="mb-6">
          <button
            onClick={() => setShowVideoModal(true)}
            className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 font-semibold flex items-center gap-2 transition-colors"
          >
            ▶ Watch Video
          </button>
        </div>
      )}

      {/* Gallery Modal */}
      {showGallery && images.length > 0 && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setShowGallery(false)}
        >
          <div className="relative max-w-5xl w-full" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowGallery(false)}
              className="absolute top-4 right-4 bg-white/90 text-gray-800 px-4 py-2 rounded-lg hover:bg-white font-medium z-10"
            >
              ✕ Close
            </button>
            <img
              src={images[currentIndex]?.url || ''}
              alt={`${offerName} - Image ${currentIndex + 1}`}
              className="w-full h-auto rounded-lg"
              onError={(e) => {
                console.error('Failed to load gallery image')
                e.currentTarget.style.display = 'none'
              }}
            />
            {images.length > 1 && (
              <>
                <button
                  onClick={() => setCurrentIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1))}
                  className="absolute left-4 top-1/2 -translate-y-1/2 bg-white/90 text-gray-800 p-3 rounded-full hover:bg-white"
                >
                  ←
                </button>
                <button
                  onClick={() => setCurrentIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0))}
                  className="absolute right-4 top-1/2 -translate-y-1/2 bg-white/90 text-gray-800 p-3 rounded-full hover:bg-white"
                >
                  →
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Video Modal */}
      {showVideoModal && promoVideo && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setShowVideoModal(false)}
        >
          <div className="relative max-w-4xl w-full" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowVideoModal(false)}
              className="absolute top-4 right-4 bg-white/90 text-gray-800 px-4 py-2 rounded-lg hover:bg-white font-medium z-10"
            >
              ✕ Close
            </button>
            {promoVideo?.url ? (
              promoVideo.url.includes('youtube.com') || promoVideo.url.includes('youtu.be') || promoVideo.url.includes('vimeo.com') ? (
                <iframe
                  src={promoVideo.url}
                  className="w-full aspect-video rounded-lg"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              ) : (
                <video
                  src={promoVideo.url}
                  controls
                  className="w-full rounded-lg"
                />
              )
            ) : (
              <div className="bg-gray-800 rounded-lg p-8 text-center text-white">
                <p>Video URL not available</p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}

