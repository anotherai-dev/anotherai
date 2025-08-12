export default function LoadingState() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/2 mb-6"></div>
        <div className="space-y-6">
          <div className="bg-gray-100 rounded-lg p-6">
            <div className="h-6 bg-gray-200 rounded w-1/4 mb-3"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
          <div className="bg-gray-100 rounded-lg p-6">
            <div className="h-6 bg-gray-200 rounded w-1/4 mb-3"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
