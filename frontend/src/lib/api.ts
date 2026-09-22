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

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const response = await fetch(apiUrl(path), {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...init.headers,
    },
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`;

    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Keep the safe fallback when the server returns no JSON body.
    }

    throw new Error(detail);
  }

  return response;
}

// Retained only for an explicit local/mock walkthrough mode.
// Do not use this flag as a security boundary.
export const IS_PUBLIC_DEMO =
  process.env.NEXT_PUBLIC_DEMO_MODE === "true";
