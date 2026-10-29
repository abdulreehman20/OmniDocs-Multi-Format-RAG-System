"use client";

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
  state: "idle" | "uploading" | "processing" | "error" | "done";
  error?: string;
  documentId?: string;
};

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
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
    updateItem(item.id, { state: "uploading", progress: 0, error: undefined });
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
      await putFileToPresignedUrl(init.put_url, item.file, (pct) =>
        updateItem(item.id, { progress: pct }),
      );
      updateItem(item.id, { state: "processing", progress: 100, documentId: init.document_id });
      await completeUpload(init.document_id);
      updateItem(item.id, { state: "done", documentId: init.document_id });
      onUploaded();
    } catch (err) {
      updateItem(item.id, {
        state: "error",
        error: err instanceof Error ? err.message : "Upload failed",
      });
    }
  };

  const enqueueFiles = useCallback(
    (files: FileList | File[]) => {
      const list = Array.from(files).slice(0, limits.max_files_per_selection);
      const next: QueueItem[] = list.map((file) => ({
        id: crypto.randomUUID(),
        file,
        progress: 0,
        state: "idle",
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
          Drag and drop Markdown, TXT, PDF, CSV, or DOCX files. Max {limits.max_files_per_selection}{" "}
          files, {formatBytes(limits.max_file_size_bytes)} each.
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
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{item.file.name}</p>
                <p className="text-xs text-zinc-500">
                  {formatBytes(item.file.size)} · {item.state}
                  {item.error ? ` — ${item.error}` : ""}
                </p>
              </div>
              {item.state === "error" ? (
                <Button type="button" variant="outline" size="sm" onClick={() => void uploadOne(item)}>
                  Retry
                </Button>
              ) : null}
            </div>
            {(item.state === "uploading" || item.state === "processing") && (
              <Progress value={item.progress} className="mt-2" />
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
