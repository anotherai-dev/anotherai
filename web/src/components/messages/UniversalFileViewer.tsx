import { XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { FileView } from "@/components/messages/FileView";
import { File } from "@/types/models";

interface UniversalFileViewerProps {
  url: string;
}

interface FileInfo {
  contentType: string;
  dataUrl?: string;
  url: string;
}

function isImageType(contentType: string): boolean {
  return contentType.startsWith("image/");
}

function detectContentTypeFromExtension(url: string): string | null {
  const extension = url.split(".").pop()?.toLowerCase();
  const extensionMap: Record<string, string> = {
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    png: "image/png",
    gif: "image/gif",
    webp: "image/webp",
    svg: "image/svg+xml",
    pdf: "application/pdf",
    mp3: "audio/mpeg",
    wav: "audio/wav",
    ogg: "audio/ogg",
    m4a: "audio/mp4",
    aac: "audio/aac",
    flac: "audio/flac",
    txt: "text/plain",
    json: "application/json",
    csv: "text/csv",
    xml: "application/xml",
    html: "text/html",
    md: "text/markdown",
  };
  return extension ? extensionMap[extension] || null : null;
}

async function downloadAndAnalyzeFile(url: string): Promise<FileInfo> {
  // Try to detect content type from URL extension first
  const detectedType = detectContentTypeFromExtension(url);
  if (detectedType) {
    return {
      contentType: detectedType,
      url,
    };
  }

  // Download file to determine content type
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch file: ${response.statusText}`);
    }

    const contentType = response.headers.get("content-type") || "application/octet-stream";

    // For images, convert to data URL for ImageViewer
    if (isImageType(contentType)) {
      const blob = await response.blob();
      const dataUrl = await new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.readAsDataURL(blob);
      });

      return {
        contentType,
        dataUrl,
        url,
      };
    }

    return {
      contentType,
      url,
    };
  } catch (error) {
    console.error("Failed to analyze file:", error);
    // Fallback to generic file type
    return {
      contentType: "application/octet-stream",
      url,
    };
  }
}

export function UniversalFileViewer({ url }: UniversalFileViewerProps) {
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    const analyzeFile = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const info = await downloadAndAnalyzeFile(url);

        if (!isCancelled) {
          setFileInfo(info);
        }
      } catch (err) {
        if (!isCancelled) {
          console.error("Error analyzing file:", err);
          setError(err instanceof Error ? err.message : "Failed to analyze file");
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };

    analyzeFile();

    return () => {
      isCancelled = true;
    };
  }, [url]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center w-32 h-24 bg-gray-100 border border-gray-200 rounded-md">
        <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-gray-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-md text-red-700">
        <XCircle className="w-4 h-4 flex-shrink-0" />
        <div className="text-sm">
          <div>Failed to load file</div>
          <div className="text-xs text-red-500 mt-1">{error}</div>
        </div>
      </div>
    );
  }

  // Create a File object with the detected content type and use FileView
  const enhancedFile: File = {
    content_type: fileInfo?.contentType ?? "application/octet-stream",
    url: fileInfo?.dataUrl ?? fileInfo?.url ?? url,
  };

  return <FileView file={enhancedFile} />;
}
