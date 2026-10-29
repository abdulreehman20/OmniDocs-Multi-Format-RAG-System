import Link from "next/link";
import { connection } from "next/server";

import { SignOutButton } from "@/components/layout/sign-out-button";
import { auth } from "@/lib/auth/server";

export async function DashboardShell({ children }: { children: React.ReactNode }) {
  await connection();
  const { data: session } = await auth.getSession();

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <nav className="flex items-center gap-4 text-sm font-medium">
            <Link href="/documents">Documents</Link>
            <Link href="/chat">Chat</Link>
            <Link href="/settings">Settings</Link>
          </nav>
          <div className="flex items-center gap-3 text-sm text-zinc-600">
            <span className="hidden sm:inline">{session?.user?.email || session?.user?.name}</span>
            <SignOutButton />
          </div>
        </div>
      </header>
      <div className="mx-auto max-w-5xl px-4 py-6">{children}</div>
    </div>
  );
}
