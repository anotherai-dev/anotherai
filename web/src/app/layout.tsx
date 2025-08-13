import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Image from "next/image";
import { Suspense } from "react";
import LayoutContent from "@/components/LayoutContent";
import { ToastProvider } from "@/components/ToastProvider";
import { ApiKeysModal } from "@/components/api-keys-modal/ApiKeysModal";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { SignInButton } from "@/components/auth/SignInButton";
import { SignUpButton } from "@/components/auth/SignUpButton";
import { SignedIn } from "@/components/auth/SignedIn";
import { SignedOut } from "@/components/auth/SignedOut";
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
    "Discover the newest and most powerful AI models from AnotherAI. View quality scores, pricing, capabilities, and release dates.",
  keywords: [
    "AI",
    "AnotherAI",
    "models",
    "artificial intelligence",
    "API",
    "machine learning",
  ],
  authors: [{ name: "AnotherAI Model Explorer" }],
  openGraph: {
    title: "AnotherAI",
    description:
      "Discover the newest and most powerful AI models from AnotherAI",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AuthProvider>
          <ToastProvider>
            <SignedOut>
              <div className="flex flex-col w-full h-screen bg-gray-50 justify-center items-center px-4">
                <div className="bg-white rounded-[2px] border border-gray-200 p-6 max-w-md w-full text-center shadow-sm">
                  {/* Logo and Title */}
                  <div className="flex items-center justify-center gap-3 mb-6">
                    <Image
                      src="/sidebar-logo.png"
                      alt="AnotherAI Logo"
                      width={40}
                      height={40}
                      className="w-10 h-10"
                    />
                    <h1 className="text-2xl font-semibold text-gray-900">
                      AnotherAI
                    </h1>
                  </div>

                  <div className="mb-6">
                    <p className="text-sm text-gray-600">
                      Please sign in to continue
                    </p>
                  </div>

                  <div className="space-y-2">
                    <SignInButton>
                      <button className="w-full bg-blue-600 text-white hover:bg-blue-700 cursor-pointer px-6 py-2 rounded-[2px] font-medium transition-colors duration-200">
                        Sign In
                      </button>
                    </SignInButton>
                    <div>
                      <span className="text-gray-600 text-sm">{`Don't have an account? `}</span>
                      <SignUpButton>
                        <button className="text-gray-900 hover:text-gray-700 text-sm font-medium transition-colors duration-200 cursor-pointer">
                          Sign Up
                        </button>
                      </SignUpButton>
                    </div>
                  </div>
                </div>
              </div>
            </SignedOut>
            <SignedIn>
              <LayoutContent>{children}</LayoutContent>
            </SignedIn>

            <Suspense fallback={null}>
              <CompletionModal />
              <DeploymentModal />
              <ApiKeysModal />
            </Suspense>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
