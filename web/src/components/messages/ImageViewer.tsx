import Image from "next/image";
import { useEffect, useState } from "react";
import { Modal } from "@/components/Modal";

interface ImageViewerProps {
  imageUrl: string;
  alt?: string;
  className?: string;
}

export function ImageViewer({ imageUrl, alt = "Image", className }: ImageViewerProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  // Use regular img only for data URIs, Next.js Image for everything else
  const isDataUri = imageUrl.startsWith("data:");
  const shouldUseRegularImg = isDataUri;

  // Auto-clear loading state for Next.js Images after a short delay
  useEffect(() => {
    if (!shouldUseRegularImg) {
      const timer = setTimeout(() => {
        setIsLoading(false);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [shouldUseRegularImg]);

  const handleImageLoad = () => {
    setIsLoading(false);
    setHasError(false);
  };

  const handleImageError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  if (hasError) {
    return (
      <div className="flex items-center gap-2 p-3 bg-gray-50 border border-gray-200 rounded-md text-gray-600">
        <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
            clipRule="evenodd"
          />
        </svg>
        <div className="text-sm">
          <div>Failed to load image</div>
          <div className="text-xs text-gray-500 mt-1 break-all">{imageUrl}</div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={`relative w-full ${className}`}>
        {isLoading && (
          <div className="flex items-center justify-center w-32 h-24 bg-gray-100 border border-gray-200 rounded-md">
            <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-gray-600"></div>
          </div>
        )}
        {shouldUseRegularImg ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={alt}
            className={`w-auto h-auto max-w-full max-h-48 rounded-md shadow-sm border border-gray-200 cursor-pointer hover:shadow-md transition-shadow object-contain ${
              isLoading ? "hidden" : "block"
            }`}
            onLoad={handleImageLoad}
            onError={handleImageError}
            onClick={() => setIsModalOpen(true)}
          />
        ) : (
          <Image
            src={imageUrl}
            alt={alt}
            width={0}
            height={0}
            sizes="100vw"
            className={`w-auto h-auto max-w-full max-h-48 rounded-md shadow-sm border border-gray-200 cursor-pointer hover:shadow-md transition-shadow object-contain ${
              isLoading ? "hidden" : "block"
            }`}
            onLoadingComplete={handleImageLoad}
            onLoad={handleImageLoad}
            onError={handleImageError}
            onClick={() => setIsModalOpen(true)}
            priority={false}
          />
        )}
      </div>

      {/* Modal for enlarged view */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}>
        <div className="relative max-w-4xl max-h-[90vh] bg-white rounded-lg shadow-xl">
          {shouldUseRegularImg ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imageUrl}
              alt={alt}
              className="w-auto h-auto min-w-[400px] min-h-[300px] max-w-full max-h-[85vh] object-contain rounded-lg"
            />
          ) : (
            <Image
              src={imageUrl}
              alt={alt}
              width={0}
              height={0}
              sizes="100vw"
              className="w-auto h-auto min-w-[400px] min-h-[300px] max-w-full max-h-[85vh] object-contain rounded-lg"
              priority={true}
            />
          )}
          <button
            onClick={() => setIsModalOpen(false)}
            className="absolute top-4 right-4 bg-black/50 hover:bg-black/70 text-white p-2 rounded-full transition-colors cursor-pointer"
            aria-label="Close image"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </Modal>
    </>
  );
}
