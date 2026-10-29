"use server";

import { auth } from "@/lib/auth/server";
import { syncAppUser } from "@/lib/auth/sync-app-user";
import { redirect } from "next/navigation";

export async function signInWithEmail(
  _prevState: { error: string } | null,
  formData: FormData,
) {
  const { error } = await auth.signIn.email({
    email: formData.get("email") as string,
    password: formData.get("password") as string,
  });

  if (error) {
    return { error: error.message || "Failed to sign in. Try again" };
  }

  await syncAppUser();
  redirect("/documents");
}
