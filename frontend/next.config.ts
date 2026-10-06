import type { NextConfig } from "next";

// NEXT_PUBLIC_API_URL is inlined at build time. A Vercel build without it
// would quietly point every visitor's browser at http://localhost:8000.
if (process.env.VERCEL && !process.env.NEXT_PUBLIC_API_URL) {
  throw new Error(
    "NEXT_PUBLIC_API_URL must be set for Vercel builds (see frontend/.env.local.example).",
  );
}

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    "*.loca.lt",
    "*.trycloudflare.com",
    "*.devtunnels.ms",
    "*.asse.devtunnels.ms",
  ],
  async redirects() {
    return [
      {
        source: "/login",
        destination: "/sign-in",
        permanent: false,
      },
      {
        source: "/auth",
        destination: "/sign-in",
        permanent: false,
      },
    ];
  },
  async rewrites() {
    const backendUrl = process.env.INTERNAL_BACKEND_URL || "http://127.0.0.1:8000";
    return [
      { source: "/api/:path*", destination: `${backendUrl}/:path*` },
      { source: "/samples/:path*", destination: `${backendUrl}/samples/:path*` },
      { source: "/reads/:path*", destination: `${backendUrl}/reads/:path*` },
      { source: "/capabilities", destination: `${backendUrl}/capabilities` },
      { source: "/health", destination: `${backendUrl}/health` },
      { source: "/plan", destination: `${backendUrl}/plan` },
      { source: "/auth/:path*", destination: `${backendUrl}/auth/:path*` },
      { source: "/scans/:path*", destination: `${backendUrl}/scans/:path*` },
      { source: "/account/:path*", destination: `${backendUrl}/account/:path*` },
      { source: "/account", destination: `${backendUrl}/account` },
    ];
  },
};

export default nextConfig;
