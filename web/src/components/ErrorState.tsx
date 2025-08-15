import NotFound from "@/app/not-found";

type Props = {
  error?: string;
  onRetry: () => void;
  title?: string;
  errorCode?: number;
};

export default function ErrorState(props: Props) {
  const { error, onRetry, title = "Error", errorCode } = props;

  // Check if error message contains 404 or if errorCode is 404
  const is404 = errorCode === 404 || (error && error.includes("404"));

  if (is404) {
    return <NotFound />;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h2 className="text-red-800 font-semibold mb-2">{title}</h2>
        <p className="text-red-600">{error || "An error occurred"}</p>
        <div className="mt-4 space-x-4">
          <button onClick={onRetry} className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">
            Retry
          </button>
        </div>
      </div>
    </div>
  );
}
