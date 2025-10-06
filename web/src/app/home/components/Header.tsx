import Image from "next/image";
import { SignInButton, SignUpButton } from "@/auth/components";

export function Header() {
  return (
    <header className="sticky top-0 z-50 bg-gray-50 border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center gap-2">
            <Image src="/sidebar-logo.png" alt="AnotherAI Logo" width={28} height={28} className="w-7 h-7" />
            <span className="text-lg font-medium text-gray-900">AnotherAI</span>
          </div>
          <nav className="hidden md:flex items-center gap-8">
            <a
              href="https://docs.anotherai.dev"
              className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              Documentation
            </a>
            <a href="#compare-models" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
              Compare Models
            </a>
            <a href="#ai-learns" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
              AI Learning
            </a>
            <a href="#try-it" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
              Try it
            </a>
          </nav>
          <div className="flex items-center gap-3">
            <SignInButton>
              <button className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 bg-gray-200 hover:bg-gray-300 rounded transition-all duration-200 cursor-pointer">
                Sign In
              </button>
            </SignInButton>
            <SignUpButton>
              <button className="px-4 py-2 bg-gray-900 text-white hover:bg-gray-800 rounded text-sm font-medium transition-all duration-200 cursor-pointer shadow-sm hover:shadow-md">
                Get Started
              </button>
            </SignUpButton>
          </div>
        </div>
      </div>
    </header>
  );
}
