"use client";

import { File, FileSpreadsheet, FileText, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  completeUpload,
  initUpload,
  putFileToPresignedUrl,
} from "@/lib/api-client/client";
import type { UploadLimits } from "@/lib/api-client/types";

type QueueItem = {
  id: string;
  file: File;
  progress: number;
  state: "idle" | "uploading" | "completing" | "queued" | "error" | "done" | "cancelled";
  phase: "upload" | "ingest" | "idle";
  error?: string;
  documentId?: string;
  abort?: AbortController;
};

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function FileGlyph({ name }: { name: string }) {
  const lower = name.toLowerCase();
  if (lower.endsWith(".csv")) return <FileSpreadsheet className="size-4 text-zinc-500" />;
  if (lower.endsWith(".pdf")) return <FileText className="size-4 text-zinc-500" />;
  return <File className="size-4 text-zinc-500" />;
}

export function UploadPanel({
  limits,
  onUploaded,
}: {
  limits: UploadLimits;
  onUploaded: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<QueueItem[]>([]);
  const [dragOver, setDragOver] = useState(false);

  const accepted = limits.accepted_extensions;

  const updateItem = (id: string, patch: Partial<QueueItem>) => {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  };

  const uploadOne = async (item: QueueItem) => {
    const abort = new AbortController();
    updateItem(item.id, {
      state: "uploading",
      phase: "upload",
      progress: 0,
      error: undefined,
      abort,
    });
    try {
      if (item.file.size > limits.max_file_size_bytes) {
        throw new Error(`File exceeds ${formatBytes(limits.max_file_size_bytes)} limit`);
      }
      const init = await initUpload({
        filename: item.file.name,
        mime_type: item.file.type || "application/octet-stream",
        byte_size: item.file.size,
        idempotency_key: crypto.randomUUID(),
      });
      if (!init.put_url) {
        throw new Error("No upload URL returned");
      }
      await putFileToPresignedUrl(
        init.put_url,
        item.file,
        (pct) => updateItem(item.id, { progress: pct }),
        abort.signal,
      );
      updateItem(item.id, {
        state: "completing",
        phase: "ingest",
        progress: 100,
        documentId: init.document_id,
        abort: undefined,
      });
      await completeUpload(init.document_id);
      updateItem(item.id, {
        state: "queued",
        phase: "ingest",
        documentId: init.document_id,
      });
      onUploaded();
      updateItem(item.id, { state: "done", phase: "ingest" });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        updateItem(item.id, {
          state: "cancelled",
          phase: "idle",
          error: "Upload cancelled",
          abort: undefined,
        });
        return;
      }
      updateItem(item.id, {
        state: "error",
        phase: "idle",
        error: err instanceof Error ? err.message : "Upload failed",
        abort: undefined,
      });
    }
  };

  const cancelItem = (item: QueueItem) => {
    item.abort?.abort();
    updateItem(item.id, {
      state: "cancelled",
      phase: "idle",
      error: "Upload cancelled",
      abort: undefined,
    });
  };

  const enqueueFiles = useCallback(
    (files: FileList | File[]) => {
      const list = Array.from(files).slice(0, limits.max_files_per_selection);
      const next: QueueItem[] = list.map((file) => ({
        id: crypto.randomUUID(),
        file,
        progress: 0,
        state: "idle",
        phase: "idle",
      }));
      setItems((prev) => [...next, ...prev].slice(0, limits.max_files_per_selection * 2));
      for (const item of next) {
        void uploadOne(item);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [limits],
  );

  return (
    <div className="space-y-4">
      <div
        className={`flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragOver ? "border-zinc-900 bg-zinc-100" : "border-zinc-300 bg-zinc-50"
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files?.length) enqueueFiles(e.dataTransfer.files);
        }}
      >
        <h2 className="text-lg font-medium">Upload documents</h2>
        <p className="max-w-md text-sm text-zinc-500">
          Drag and drop or choose from My Device. Supported: Markdown, TXT, PDF, CSV, DOCX.
          Max {limits.max_files_per_selection} files, {formatBytes(limits.max_file_size_bytes)}{" "}
          each. Limits come from the server—not sample UI values.
        </p>
        <Button type="button" onClick={() => inputRef.current?.click()}>
          My Device
        </Button>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          multiple
          accept={accepted}
          onChange={(e) => {
            if (e.target.files?.length) enqueueFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item.id} className="rounded-lg border bg-white p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <FileGlyph name={item.file.name} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{item.file.name}</p>
                  <p className="text-xs text-zinc-500">
                    {formatBytes(item.file.size)}
                    {item.phase === "upload" ? " · Upload progress" : ""}
                    {item.phase === "ingest" ? " · Ingestion / queue" : ""}
                    {item.state === "error" || item.state === "cancelled"
                      ? ` — ${item.error || item.state}`
                      : ` · ${item.state}`}
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                {item.state === "uploading" ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label="Cancel upload"
                    onClick={() => cancelItem(item)}
                  >
                    <X className="size-4" />
                  </Button>
                ) : null}
                {item.state === "error" || item.state === "cancelled" ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => void uploadOne(item)}
                  >
                    Retry
                  </Button>
                ) : null}
              </div>
            </div>
            {(item.state === "uploading" || item.state === "completing") && (
              <Progress value={item.progress} className="mt-2" />
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
