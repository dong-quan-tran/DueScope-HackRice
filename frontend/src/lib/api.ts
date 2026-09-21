const configuredApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");

const isProduction = process.env.NODE_ENV === "production";

if (isProduction && !configuredApiBaseUrl) {
  throw new Error(
    "Missing NEXT_PUBLIC_API_BASE_URL. Configure the deployed backend URL in Vercel and redeploy."
  );
}

export const API_BASE_URL =
  configuredApiBaseUrl ?? "http://127.0.0.1:8001";

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

// Retained only for an explicit local/mock walkthrough mode.
// Do not use this flag as a security boundary.
export const IS_PUBLIC_DEMO =
  process.env.NEXT_PUBLIC_DEMO_MODE === "true";
