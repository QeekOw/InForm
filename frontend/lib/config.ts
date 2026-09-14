// Where the browser reaches the FastAPI backend. Vercel builds must set
// NEXT_PUBLIC_API_URL (next.config.ts refuses to build without it); the
// localhost default is only for `npm run dev`.
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
