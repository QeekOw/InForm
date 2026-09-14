// Centralized client/runtime configuration.

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

if (
  typeof window !== "undefined" &&
  process.env.NODE_ENV === "production" &&
  !process.env.NEXT_PUBLIC_API_URL
) {
  console.warn(
    "[InForm] NEXT_PUBLIC_API_URL is not set in production build; falling back to http://localhost:8000.",
  );
}
