import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Suspense } from "react";
import LayoutContent from "@/components/LayoutContent";
import { ToastProvider } from "@/components/ToastProvider";
import { ApiKeysModal } from "@/components/api-keys-modal/ApiKeysModal";
import { ConditionalClerkProvider } from "@/components/auth/ConditionalClerkProvider";
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
  keywords: ["AI", "AnotherAI", "models", "artificial intelligence", "API", "machine learning"],
  authors: [{ name: "AnotherAI Model Explorer" }],
  openGraph: {
    title: "AnotherAI",
    description: "Discover the newest and most powerful AI models from AnotherAI",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <ToastProvider>
          <ConditionalClerkProvider>
            <LayoutContent>{children}</LayoutContent>
          </ConditionalClerkProvider>

          <Suspense fallback={null}>
            <CompletionModal />
            <DeploymentModal />
            <ApiKeysModal />
          </Suspense>
        </ToastProvider>
      </body>
    </html>
  );
}
