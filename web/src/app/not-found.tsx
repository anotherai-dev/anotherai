import Link from "next/link";
import { HeaderSection } from "@/components/HeaderSection";

export default function NotFound() {
  return (
    <div className="flex flex-col w-full h-full mx-auto px-4 py-8 gap-6 bg-gray-50 justify-center items-center">
      <div className="max-w-2xl mx-auto text-center">
        {/* 404 Header */}
        <div className="mb-8">
          <div className="text-6xl font-bold text-gray-400 mb-4">404</div>
          <HeaderSection
            title="Page Not Found"
            description="The page you're looking for doesn't exist or has been moved."
            className="text-center"
          />
        </div>

        {/* Helpful Links */}
        <div className="bg-white rounded-[2px] border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Popular pages</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Link
              href="/completions"
              className="flex flex-col items-center p-4 bg-gray-50 hover:bg-gray-100 rounded-[2px] transition-colors duration-200"
            >
              <div className="w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center mb-2">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
              </div>
              <span className="font-medium text-gray-900 text-sm">Completions</span>
              <span className="text-xs text-gray-600 text-center">View completion history</span>
            </Link>

            <Link
              href="/agents"
              className="flex flex-col items-center p-4 bg-gray-50 hover:bg-gray-100 rounded-[2px] transition-colors duration-200"
            >
              <div className="w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center mb-2">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
              </div>
              <span className="font-medium text-gray-900 text-sm">Agents</span>
              <span className="text-xs text-gray-600 text-center">Explore AI agents</span>
            </Link>

            <Link
              href="/experiments"
              className="flex flex-col items-center p-4 bg-gray-50 hover:bg-gray-100 rounded-[2px] transition-colors duration-200"
            >
              <div className="w-10 h-10 bg-gray-600 rounded-full flex items-center justify-center mb-2">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
                  />
                </svg>
              </div>
              <span className="font-medium text-gray-900 text-sm">Experiments</span>
              <span className="text-xs text-gray-600 text-center">Browse experiments</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
