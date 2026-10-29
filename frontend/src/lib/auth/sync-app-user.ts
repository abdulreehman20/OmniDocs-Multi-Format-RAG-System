"use server";

import { auth } from "@/lib/auth/server";

/**
 * Ensure the authenticated Neon Auth user exists in the app `users` table.
 * FastAPI `get_current_user` upserts on any authenticated request (e.g. /limits).
 */
export async function syncAppUser(): Promise<boolean> {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const { data, error } = await auth.token();
  if (error || !data?.token) {
    return false;
  }

  try {
    const response = await fetch(`${apiBase}/api/v1/limits`, {
      headers: { Authorization: `Bearer ${data.token}` },
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
}
