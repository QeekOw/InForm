// Where the browser reaches the FastAPI backend.
// In the browser, defaults to relative "" so Next.js proxies to the backend
// seamlessly regardless of whether accessed via localhost, 127.0.0.1, or remote tunnel.
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? "" : "http://127.0.0.1:8000");
