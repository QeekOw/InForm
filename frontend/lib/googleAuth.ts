import { API_URL } from "@/lib/config";

export function googleSignInUrl(redirectPath: string | null): string {
  const params = new URLSearchParams();
  if (redirectPath) params.set("redirect", redirectPath);
  const query = params.toString();
  return `${API_URL}/auth/google/start${query ? `?${query}` : ""}`;
}

export function googleSignInStatusMessage(status: string | null): string | null {
  switch (status) {
    case "unavailable":
      return "Google sign-in isn't configured yet. Use your email and password, or continue as a guest.";
    case "cancelled":
      return "Google sign-in was cancelled.";
    case "error":
      return "Google sign-in failed. Please try again or use your email and password.";
    default:
      return null;
  }
}
