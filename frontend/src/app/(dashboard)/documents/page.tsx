"use client";

import { useCallback, useEffect, useState } from "react";

import { DocumentList } from "@/components/documents/document-list";
import { UploadPanel } from "@/components/upload/upload-panel";
import { getLimits, listDocuments } from "@/lib/api-client/client";
import type { DocumentRecord, UploadLimits } from "@/lib/api-client/types";

export default function DocumentsPage() {
  const [limits, setLimits] = useState<UploadLimits | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [nextLimits, nextDocs] = await Promise.all([getLimits(), listDocuments()]);
      setLimits(nextLimits);
      setDocuments(nextDocs);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Upload supported files, monitor queue status, download or delete your documents.
        </p>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {limits ? <UploadPanel limits={limits} onUploaded={() => void refresh()} /> : (
        <p className="text-sm text-zinc-500">Loading upload limits…</p>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Your library</h2>
        <DocumentList documents={documents} onChanged={() => void refresh()} />
      </section>
    </div>
  );
}
