import { Suspense } from "react";

import { DashboardShell } from "@/components/layout/dashboard-shell";
import { syncAppUser } from "@/lib/auth/sync-app-user";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Upsert into app `users` on every dashboard visit (JWT → FastAPI → DB).
  await syncAppUser();

  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-zinc-500">
          Loading…
        </div>
      }
    >
      <DashboardShell>{children}</DashboardShell>
    </Suspense>
  );
}
