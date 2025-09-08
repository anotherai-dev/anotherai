import { Volume2 } from "lucide-react";
import { useState } from "react";

interface AudioViewerProps {
  audioUrl: string;
  className?: string;
}

export function AudioViewer({ audioUrl, className }: AudioViewerProps) {
  const [hasError, setHasError] = useState(false);

  const handleAudioError = () => {
    setHasError(true);
  };

  if (hasError) {
    return (
      <div className="flex items-center gap-2 p-3 bg-gray-50 border border-gray-200 rounded-md text-gray-600">
        <Volume2 className="w-4 h-4 flex-shrink-0" />
        <div className="text-sm">
          <div>Failed to load audio</div>
          <div className="text-xs text-gray-500 mt-1 break-all">{audioUrl}</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`}>
      <div className="bg-gray-50 border border-gray-200 rounded-[4px] p-3">
        <div className="flex items-center gap-2 mb-2">
          <Volume2 className="w-4 h-4 text-gray-600" />
          <span className="text-xs font-semibold text-gray-800">Audio</span>
        </div>
        <audio controls className="w-full h-8" onError={handleAudioError} preload="metadata">
          <source src={audioUrl} />
          Your browser does not support the audio element.
        </audio>
      </div>
    </div>
  );
}
