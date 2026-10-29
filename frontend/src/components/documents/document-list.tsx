"use client";

import { Button } from "@/components/ui/button";
import { deleteDocument, downloadDocument } from "@/lib/api-client/client";
import type { DocumentRecord } from "@/lib/api-client/types";

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentList({
  documents,
  onChanged,
}: {
  documents: DocumentRecord[];
  onChanged: () => void;
}) {
  if (documents.length === 0) {
    return (
      <p className="rounded-xl border border-dashed bg-zinc-50 px-4 py-8 text-center text-sm text-zinc-500">
        No documents yet. Upload Markdown, TXT, PDF, CSV, or DOCX to get started.
      </p>
    );
  }

  return (
    <ul className="divide-y rounded-xl border bg-white">
      {documents.map((doc) => (
        <li key={doc.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="min-w-0">
            <p className="truncate font-medium">{doc.filename}</p>
            <p className="text-xs text-zinc-500">
              {doc.source_type} · {formatBytes(doc.byte_size)} · {doc.status}
              {doc.status_message ? ` · ${doc.status_message}` : ""}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={doc.status === "upload_pending" || doc.status === "deleting"}
              onClick={async () => {
                const result = await downloadDocument(doc.id);
                window.open(result.download_url, "_blank", "noopener,noreferrer");
              }}
            >
              Download
            </Button>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              disabled={doc.status === "deleting" || doc.status === "deleted"}
              onClick={async () => {
                await deleteDocument(doc.id);
                onChanged();
              }}
            >
              Delete
            </Button>
          </div>
        </li>
      ))}
    </ul>
  );
}
