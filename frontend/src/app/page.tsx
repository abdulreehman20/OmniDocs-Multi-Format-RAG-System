import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";

import { auth } from "@/lib/auth/server";

async function HomeContent() {
  await connection();
  const { data: session } = await auth.getSession();

  return (
    <main className="min-h-screen bg-zinc-50">
      <div className="mx-auto flex max-w-3xl flex-col gap-10 px-4 py-16 sm:py-24">
        <div className="space-y-4">
          <p className="text-sm font-medium tracking-wide text-zinc-500">rag-basic</p>
          <h1 className="text-4xl font-semibold tracking-tight text-zinc-900 sm:text-5xl">
            Ask your documents. Get cited answers.
          </h1>
          <p className="max-w-2xl text-lg text-zinc-600">
            Upload Markdown, TXT, PDF, CSV, and DOCX files. We ingest them in the background,
            then you can chat with grounded answers that link back to source locations. Answers
            are only as good as the evidence in your selected documents—we do not promise
            absolute accuracy.
          </p>
        </div>

        <ul className="grid gap-3 text-sm text-zinc-700 sm:grid-cols-3">
          <li className="rounded-lg border border-zinc-200 bg-white p-4">
            <p className="font-medium text-zinc-900">Supported files</p>
            <p className="mt-1 text-zinc-600">.md · .txt · .pdf · .csv · .docx</p>
          </li>
          <li className="rounded-lg border border-zinc-200 bg-white p-4">
            <p className="font-medium text-zinc-900">Background ingest</p>
            <p className="mt-1 text-zinc-600">Track progress until documents are ready.</p>
          </li>
          <li className="rounded-lg border border-zinc-200 bg-white p-4">
            <p className="font-medium text-zinc-900">Cited Q&amp;A</p>
            <p className="mt-1 text-zinc-600">Streamed answers with verifiable source labels.</p>
          </li>
        </ul>

        <div className="flex flex-wrap gap-3">
          {session?.user ? (
            <>
              <Link
                href="/documents"
                className="inline-flex h-10 items-center rounded-lg bg-zinc-900 px-5 text-sm font-medium text-white"
              >
                Open documents
              </Link>
              <Link
                href="/chat"
                className="inline-flex h-10 items-center rounded-lg border border-zinc-300 bg-white px-5 text-sm font-medium"
              >
                Open chat
              </Link>
            </>
          ) : (
            <>
              <Link
                href="/auth/sign-in"
                className="inline-flex h-10 items-center rounded-lg bg-zinc-900 px-5 text-sm font-medium text-white"
              >
                Sign in
              </Link>
              <Link
                href="/auth/sign-up"
                className="inline-flex h-10 items-center rounded-lg border border-zinc-300 bg-white px-5 text-sm font-medium"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
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
