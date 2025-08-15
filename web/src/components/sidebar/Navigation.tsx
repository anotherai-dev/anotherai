"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navigation() {
  const pathname = usePathname();

  const isActive = (path: string) => pathname === path;

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <div className="flex items-center cursor-default">
              <Image src="/sidebar-logo.png" alt="Logo" width={32} height={32} className="rounded-md" />
            </div>

            <div className="flex space-x-4">
              <Link
                href="/agents"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive("/agents") || pathname.startsWith("/agents/")
                    ? "bg-blue-100 text-blue-700"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                }`}
              >
                Agents
              </Link>

              <Link
                href="/completions"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive("/completions")
                    ? "bg-indigo-100 text-indigo-700"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                }`}
              >
                Completions
              </Link>

              <Link
                href="/experiments"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive("/experiments")
                    ? "bg-green-100 text-green-700"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
                }`}
              >
                Experiments
              </Link>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
