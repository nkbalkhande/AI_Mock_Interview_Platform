import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    // The dev-server rewrite proxy defaults to a 30s timeout, which kills
    // long LLM-backed requests (answer/coding submission -> evaluate +
    // plan next question) with ECONNRESET before FastAPI responds.
    proxyTimeout: 180_000,
  },
  // /interviews was a leftover stub; practice flows live on the dashboard.
  async redirects() {
    return [
      {
        source: "/interviews",
        destination: "/dashboard",
        permanent: false,
      },
    ];
  },
  async rewrites() {
    // Proxy API calls to FastAPI so the browser talks to the Next.js origin only.
    const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
