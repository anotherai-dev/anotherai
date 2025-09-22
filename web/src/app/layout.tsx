import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Image from "next/image";
import { Suspense } from "react";
import { AuthProvider, SignInButton, SignUpButton, SignedIn, SignedOut } from "@/auth/components";
import LayoutContent from "@/components/LayoutContent";
import { ToastProvider } from "@/components/ToastProvider";
import { ApiKeysModal } from "@/components/api-keys-modal/ApiKeysModal";
import { CompletionModal } from "@/components/completion-modal/CompletionModal";
import { DeploymentModal } from "@/components/deployment-modal/DeploymentModal";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AnotherAI",
  description:
    "AnotherAI enables your AI assistant (ChatGPT, Claude Code, Cursor, ...) to become a powerful AI engineer.",
  keywords: ["AI", "AnotherAI", "models", "artificial intelligence", "API", "machine learning"],
  authors: [{ name: "AnotherAI Model Explorer" }],
  openGraph: {
    title: "AnotherAI",
    description:
      "AnotherAI enables your AI assistant (ChatGPT, Claude Code, Cursor, ...) to become a powerful AI engineer.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <ToastProvider>
          <AuthProvider>
            <SignedOut>
              <div className="flex flex-col w-full h-screen bg-gray-50 justify-center items-center px-4">
                <div className="bg-white rounded-[2px] border border-gray-200 p-6 max-w-md w-full text-center shadow-sm">
                  <div className="flex items-center justify-center gap-3 mb-6">
                    <Image src="/sidebar-logo.png" alt="AnotherAI Logo" width={40} height={40} className="w-10 h-10" />
                    <h1 className="text-2xl font-semibold text-gray-900">AnotherAI</h1>
                  </div>
                  <div className="mb-6">
                    <p className="text-sm text-gray-600">Please sign in to continue</p>
                  </div>
                  <div className="space-y-3">
                    <SignInButton>
                      <button className="w-full bg-blue-600 text-white hover:bg-blue-700 cursor-pointer px-6 py-2 rounded-[2px] font-medium transition-colors duration-200">
                        Sign In
                      </button>
                    </SignInButton>
                    <div>
                      <span className="text-gray-600 text-sm">{`Don't have an account? `}</span>
                      <SignUpButton>
                        <button className="text-blue-600 hover:text-blue-700 text-sm font-medium transition-colors duration-200 cursor-pointer">
                          Sign Up
                        </button>
                      </SignUpButton>
                    </div>
                    <div className="pt-2 border-t border-gray-200">
                      <span className="text-gray-600 text-sm">Want to learn more? </span>
                      <a
                        href="https://docs.anotherai.dev"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-700 text-sm font-medium transition-colors duration-200 cursor-pointer"
                      >
                        Read the documentation
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </SignedOut>
            <SignedIn>
              <LayoutContent>{children}</LayoutContent>
              <Suspense fallback={null}>
                <CompletionModal />
                <DeploymentModal />
                <ApiKeysModal />
              </Suspense>
            </SignedIn>
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
