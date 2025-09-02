import type { NextConfig } from "next";

const tsconfigPath = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ? "./tsconfig.clerk.json" : "./tsconfig.json";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
      {
        protocol: "http",
        hostname: "**",
      },
    ],
    dangerouslyAllowSVG: true,
    contentDispositionType: "attachment",
    unoptimized: false,
    domains: [], // Allow all domains with the patterns above
  },
  typescript: {
    tsconfigPath,
  },
};

export default nextConfig;
