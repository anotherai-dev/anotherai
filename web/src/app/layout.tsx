import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
// import { Suspense } from "react";
// import { AuthProvider, SignedIn, SignedOut } from "@/auth/components";
// import LayoutContent from "@/components/LayoutContent";
// import SignedOutLayout from "@/components/SignedOutLayout";
// import { ToastProvider } from "@/components/ToastProvider";
// import { ApiKeysModal } from "@/components/api-keys-modal/ApiKeysModal";
// import { CompletionModal } from "@/components/completion-modal/CompletionModal";
// import { DeploymentModal } from "@/components/deployment-modal/DeploymentModal";
// import { getServerSideCookie } from "@/lib/server-cookies";
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

export default async function RootLayout() {
  // Read sidebar state from cookies server-side
  // const initialSidebarExpanded = await getServerSideCookie("sidebar-expanded", true);
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <div className="flex flex-col items-center justify-center h-screen">
          <p>
            <b>AnotherAI</b> is retired, thank you for your support.
          </p>
          <p>
            You can check the code{" "}
            <a
              href="https://github.com/anotherai-dev/anotherai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500"
            >
              on Github
            </a>
          </p>
        </div>
      </body>
    </html>
  );
}
