// Where the browser reaches the FastAPI backend. Keep the fallback identical
// during server rendering and hydration; relative paths use Next.js rewrites.
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "";
