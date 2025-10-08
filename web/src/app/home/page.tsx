import { Header } from "./components/Header";
import { getPreviewContent } from "./components/utils";

export default async function HomePage() {
  const previewData = await getPreviewContent();

  return (
    <>
      <style
        dangerouslySetInnerHTML={{
          __html: `
          body {
            background-color: #f9fafb !important;
          }
        `,
        }}
      />
      <div className="min-h-screen bg-gray-50">
        <Header />

        {/* Main Content */}
        <div className="max-w-4xl mx-auto px-6 lg:px-8 py-16">
          <div className="prose prose-gray max-w-none">
            {previewData ? (
              <>
                {previewData.title && <h1 className="text-4xl font-normal text-gray-900 mb-8">{previewData.title}</h1>}
                {previewData.content}
              </>
            ) : (
              <p className="text-red-600">Failed to load preview content. Please check the file path.</p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
