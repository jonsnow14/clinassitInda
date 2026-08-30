import type { NextConfig } from "next";

const API = process.env.API_INTERNAL_URL || "http://127.0.0.1:8002";

const nextConfig: NextConfig = {
  experimental: {
    proxyTimeout: 180_000,
  },
  async rewrites() {
    return [{ source: "/v1/:path*", destination: `${API}/v1/:path*` }];
  },
};

export default nextConfig;
