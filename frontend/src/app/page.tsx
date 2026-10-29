import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";

import { auth } from "@/lib/auth/server";

async function HomeContent() {
  await connection();
  const { data: session } = await auth.getSession();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-zinc-50 px-4">
      <div className="max-w-lg text-center">
        <h1 className="text-3xl font-semibold tracking-tight">rag-basic</h1>
        <p className="mt-3 text-zinc-600">
          Upload Markdown, TXT, PDF, CSV, and DOCX files, then ask questions with source-cited
          answers. Background ingestion and chat land in later phases.
        </p>
      </div>
      <div className="flex gap-3">
        {session?.user ? (
          <Link
            href="/documents"
            className="inline-flex h-9 items-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white"
          >
            Open documents
          </Link>
        ) : (
          <>
            <Link
              href="/auth/sign-in"
              className="inline-flex h-9 items-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white"
            >
              Sign in
            </Link>
            <Link
              href="/auth/sign-up"
              className="inline-flex h-9 items-center rounded-lg border border-zinc-300 bg-white px-4 text-sm font-medium"
            >
              Sign up
            </Link>
          </>
        )}
      </div>
    </main>
  );
}

export default function Home() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center text-sm text-zinc-500">
          Loading…
        </main>
      }
    >
      <HomeContent />
    </Suspense>
  );
}
