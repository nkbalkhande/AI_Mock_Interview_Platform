import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { NextConfig } from "next";
import { parse as parseYaml } from "yaml";

// Non-secret config lives in ../settings/config.yaml (single source of truth
// shared with the backend). No .env file is required for the frontend.
type FrontendConfig = {
  backend_url?: string;
  app_name?: string;
  api_base_url?: string;
};

function loadFrontendConfig(): Required<FrontendConfig> {
  const configPath = resolve(__dirname, "..", "settings", "config.yaml");
  const raw = readFileSync(configPath, "utf-8");
  const parsed = parseYaml(raw) as { frontend?: FrontendConfig } | null;
  const fe = parsed?.frontend ?? {};
  return {
    backend_url: fe.backend_url ?? "http://localhost:8000",
    app_name: fe.app_name ?? "AI Mock Interview Platform",
    api_base_url: fe.api_base_url ?? "/api/backend",
  };
}

const frontendConfig = loadFrontendConfig();

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Inline non-secret config into the client bundle. These replace the old
  // NEXT_PUBLIC_* env vars — `src/lib/constants.ts` reads them via process.env.
  env: {
    NEXT_PUBLIC_APP_NAME: frontendConfig.app_name,
    NEXT_PUBLIC_API_BASE_URL: frontendConfig.api_base_url,
  },
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
    return [
      {
        source: "/api/backend/:path*",
        destination: `${frontendConfig.backend_url}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
