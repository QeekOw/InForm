import type { NextConfig } from "next";

// NEXT_PUBLIC_API_URL is inlined at build time. A Vercel build without it
// would quietly point every visitor's browser at http://localhost:8000.
if (process.env.VERCEL && !process.env.NEXT_PUBLIC_API_URL) {
  throw new Error(
    "NEXT_PUBLIC_API_URL must be set for Vercel builds (see frontend/.env.local.example).",
  );
}

const nextConfig: NextConfig = {};

export default nextConfig;
