import { FileText, X } from "lucide-react";
import { useCallback, useState } from "react";
import { Modal } from "@/components/Modal";

interface PDFViewerProps {
  pdfUrl: string;
  alt?: string;
  className?: string;
}

export function PDFViewer({ pdfUrl, alt = "PDF", className }: PDFViewerProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [aspectRatio, setAspectRatio] = useState<string>("8.5 / 11"); // Default fallback

  const handlePdfLoad = useCallback((event: React.SyntheticEvent<HTMLIFrameElement>) => {
    try {
      const iframe = event.currentTarget;
      const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;

      if (iframeDoc) {
        // Try to get PDF page dimensions
        const pdfViewer = iframeDoc.querySelector("embed") || iframeDoc.querySelector("object");
        if (pdfViewer) {
          const rect = pdfViewer.getBoundingClientRect();
          if (rect.width && rect.height) {
            const ratio = rect.width / rect.height;
            setAspectRatio(`${ratio} / 1`);
          }
        }
      }
    } catch {
      // Cross-origin restrictions or other issues, use default
      console.log("Could not determine PDF dimensions, using default aspect ratio");
    }

    setIsLoading(false);
    setHasError(false);
  }, []);

  const handlePdfError = useCallback(() => {
    setIsLoading(false);
    setHasError(true);
  }, []);

  if (hasError) {
    return (
      <div className="flex items-center gap-2 p-3 bg-gray-50 border border-gray-200 rounded-md text-gray-600">
        <FileText className="w-4 h-4 flex-shrink-0" />
        <div className="text-sm">
          <div>Failed to load PDF</div>
          <div className="text-xs text-gray-500 mt-1 break-all">{pdfUrl}</div>
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
        <div
          className={`relative cursor-pointer hover:shadow-md transition-shadow overflow-hidden rounded-md shadow-sm border border-gray-200 ${
            isLoading ? "hidden" : "block"
          }`}
          onClick={() => setIsModalOpen(true)}
          style={{ aspectRatio: aspectRatio, maxWidth: "100%", maxHeight: "12rem" }} // Dynamic aspect ratio with size constraints
        >
          <iframe
            src={`${pdfUrl}#page=1&view=Fit`}
            className="w-full h-full pointer-events-none"
            onLoad={handlePdfLoad}
            onError={handlePdfError}
            title={alt}
            style={{ transform: "scale(1.05)", transformOrigin: "center" }}
          />
          <div className="absolute inset-0 bg-black/0 hover:bg-black/5 transition-colors rounded-md flex items-center justify-center" />
        </div>
      </div>

      {/* Modal for full PDF view */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}>
        <div className="relative w-[90vw] h-[90vh] bg-white rounded-lg shadow-xl">
          <iframe src={pdfUrl} className="w-full h-full rounded-lg" title={alt} />
          <button
            onClick={() => setIsModalOpen(false)}
            className="absolute top-3 right-4 bg-gray-800 hover:bg-gray-900 text-white p-2 rounded-full transition-colors cursor-pointer z-10"
            aria-label="Close PDF"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </Modal>
    </>
  );
}
