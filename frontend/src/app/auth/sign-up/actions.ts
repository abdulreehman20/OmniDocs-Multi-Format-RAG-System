"use server";

import { auth } from "@/lib/auth/server";
import { syncAppUser } from "@/lib/auth/sync-app-user";
import { redirect } from "next/navigation";

export async function signUpWithEmail(
  _prevState: { error: string } | null,
  formData: FormData,
) {
  const email = formData.get("email") as string;
  if (!email) {
    return { error: "Email address must be provided." };
  }

  const { error } = await auth.signUp.email({
    email,
    name: (formData.get("name") as string) || email,
    password: formData.get("password") as string,
  });

  if (error) {
    return { error: error.message || "Failed to create account" };
  }

  await syncAppUser();
  redirect("/documents");
}
