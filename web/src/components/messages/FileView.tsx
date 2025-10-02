import { useMemo } from "react";
import { AudioViewer } from "@/components/messages/AudioViewer";
import { ImageViewer } from "@/components/messages/ImageViewer";
import { PDFViewer } from "@/components/messages/PDFViewer";
import { File } from "@/types/models";

interface FileViewProps {
  file: File;
}

function isImageType(contentType: string): boolean {
  return contentType?.startsWith("image/") || false;
}

function isPdfType(contentType: string): boolean {
  return contentType === "application/pdf";
}

function isAudioType(contentType: string): boolean {
  return contentType?.startsWith("audio/") || false;
}

export function FileView({ file }: FileViewProps) {
  const isImage = useMemo(() => (file.content_type ? isImageType(file.content_type) : false), [file.content_type]);
  const isPdf = useMemo(() => (file.content_type ? isPdfType(file.content_type) : false), [file.content_type]);
  const isAudio = useMemo(() => (file.content_type ? isAudioType(file.content_type) : false), [file.content_type]);
  const url = useMemo(() => file.url || file.storage_url || "", [file.url, file.storage_url]);

  // For images, show the ImageViewer without the container
  if (isImage && url) {
    return <ImageViewer imageUrl={url} alt="File attachment" />;
  }

  // For PDFs, show the PDF viewer without the container
  if (isPdf && url) {
    return <PDFViewer pdfUrl={url} alt="PDF attachment" />;
  }

  // For audio, show the audio player without the container
  if (isAudio && url) {
    return <AudioViewer audioUrl={url} />;
  }

  return (
    <div className="border border-gray-200 rounded-[2px] bg-slate-50 p-3 my-2">
      <div className="mb-2">
        <span className="text-xs font-semibold text-gray-800">File Attachment</span>
      </div>

      {file.content_type && (
        <div className="mb-2">
          <span className="text-xs bg-gray-200 text-gray-900 font-medium px-2 py-1 rounded-[2px] border border-gray-300">
            {file.content_type}
          </span>
        </div>
      )}

      {file.url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-600 hover:text-blue-800 underline mt-2 break-all inline-block"
        >
          {url}
        </a>
      )}
    </div>
  );
}
