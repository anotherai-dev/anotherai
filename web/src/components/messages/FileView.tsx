import { ImageViewer } from "@/components/messages/ImageViewer";
import { File } from "@/types/models";

interface FileViewProps {
  file: File;
}

export function FileView({ file }: FileViewProps) {
  const isJpeg = file.content_type === "image/jpeg";
  const imageUrl = file.storage_url || file.url || "";

  // For JPEG, just show the ImageViewer without the container
  if (isJpeg && imageUrl) {
    return <ImageViewer imageUrl={imageUrl} alt="File attachment" />;
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

      {file.url && <div className="text-xs text-gray-600 mt-2 break-all">{file.url}</div>}
    </div>
  );
}
