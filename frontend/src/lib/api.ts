const rawApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";

export const API_BASE_URL = rawApiBaseUrl.replace(/\/$/, "");

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
export const IS_PUBLIC_DEMO =
  process.env.NEXT_PUBLIC_DEMO_MODE === "true";
