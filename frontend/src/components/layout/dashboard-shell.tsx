import { connection } from "next/server";
import { Suspense } from "react";

import { DashboardNav } from "@/components/layout/dashboard-nav";
import { auth } from "@/lib/auth/server";

export async function DashboardShell({ children }: { children: React.ReactNode }) {
  await connection();
  const { data: session } = await auth.getSession();
  const userLabel = session?.user?.email || session?.user?.name || null;

  return (
    <div className="flex min-h-screen flex-col bg-zinc-50 md:flex-row">
      <Suspense fallback={<div className="hidden w-64 border-r bg-white md:block" />}>
        <DashboardNav userLabel={userLabel} />
      </Suspense>
      <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 md:px-8 md:py-8">
        <div className="mx-auto w-full max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
