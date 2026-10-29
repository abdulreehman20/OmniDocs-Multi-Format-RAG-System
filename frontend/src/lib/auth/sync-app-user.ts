"use server";

import { auth } from "@/lib/auth/server";

/**
 * Best-effort: ensure the authenticated Neon Auth user exists in the app `users` table.
 * FastAPI `get_current_user` upserts on any authenticated request.
 */
export async function syncAppUser(): Promise<void> {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const { data, error } = await auth.token();
  if (error || !data?.token) {
    return;
  }

  try {
    await fetch(`${apiBase}/api/v1/limits`, {
      headers: { Authorization: `Bearer ${data.token}` },
      cache: "no-store",
    });
  } catch {
    // Documents page will sync on first authenticated API call.
  }
}
