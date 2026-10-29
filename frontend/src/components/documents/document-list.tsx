"use client";

import {
  File,
  FileSpreadsheet,
  FileText,
  LayoutGrid,
  List,
} from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { deleteDocument, downloadDocument, retryDocument } from "@/lib/api-client/client";
import type { DocumentRecord } from "@/lib/api-client/types";

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function FileIcon({ sourceType }: { sourceType: string }) {
  if (sourceType === "csv") return <FileSpreadsheet className="size-4 text-zinc-500" />;
  if (sourceType === "pdf") return <FileText className="size-4 text-zinc-500" />;
  return <File className="size-4 text-zinc-500" />;
}

function statusLabel(doc: DocumentRecord) {
  if (doc.status === "processing" && typeof doc.ingestion_progress === "number") {
    return `processing ${Math.round(doc.ingestion_progress * 100)}%`;
  }
  if (doc.status === "failed" && doc.error_message) {
    return `failed · ${doc.error_message}`;
  }
  if (doc.status_message && doc.status !== "ready") {
    return `${doc.status} · ${doc.status_message}`;
  }
  return doc.status;
}

const TYPE_OPTIONS = ["all", "markdown", "text", "pdf", "csv", "docx"] as const;

export function DocumentList({
  documents,
  onChanged,
}: {
  documents: DocumentRecord[];
  onChanged: () => void;
}) {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<(typeof TYPE_OPTIONS)[number]>("all");
  const [view, setView] = useState<"list" | "grid">("list");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return documents.filter((d) => {
      if (typeFilter !== "all" && d.source_type !== typeFilter) return false;
      if (!q) return true;
      return d.filename.toLowerCase().includes(q) || d.status.toLowerCase().includes(q);
    });
  }, [documents, query, typeFilter]);

  if (documents.length === 0) {
    return (
      <p className="rounded-xl border border-dashed bg-zinc-50 px-4 py-8 text-center text-sm text-zinc-500">
        No documents yet. Upload Markdown, TXT, PDF, CSV, or DOCX to get started.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search documents…"
          className="max-w-xs"
          aria-label="Search documents"
        />
        <select
          className="h-9 rounded-md border border-zinc-200 bg-white px-2 text-sm"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as (typeof TYPE_OPTIONS)[number])}
          aria-label="Filter by type"
        >
          {TYPE_OPTIONS.map((t) => (
            <option key={t} value={t}>
              {t === "all" ? "All types" : t}
            </option>
          ))}
        </select>
        <div className="ml-auto flex gap-1">
          <Button
            type="button"
            size="icon"
            variant={view === "list" ? "default" : "outline"}
            aria-label="List view"
            onClick={() => setView("list")}
          >
            <List className="size-4" />
          </Button>
          <Button
            type="button"
            size="icon"
            variant={view === "grid" ? "default" : "outline"}
            aria-label="Grid view"
            onClick={() => setView("grid")}
          >
            <LayoutGrid className="size-4" />
          </Button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-zinc-500">No documents match your filters.</p>
      ) : view === "grid" ? (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((doc) => (
            <li key={doc.id} className="rounded-xl border bg-white p-4">
              <div className="flex items-start gap-2">
                <FileIcon sourceType={doc.source_type} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{doc.filename}</p>
                  <p className="text-xs text-zinc-500">
                    {doc.source_type} · {formatBytes(doc.byte_size)}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">{statusLabel(doc)}</p>
                  <p className="text-xs text-zinc-400">{formatDate(doc.created_at)}</p>
                </div>
              </div>
              <RowActions doc={doc} onChanged={onChanged} />
            </li>
          ))}
        </ul>
      ) : (
        <div className="rounded-xl border bg-white">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>Name</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell>
                    <FileIcon sourceType={doc.source_type} />
                  </TableCell>
                  <TableCell className="max-w-[14rem] truncate font-medium">
                    {doc.filename}
                  </TableCell>
                  <TableCell>{formatBytes(doc.byte_size)}</TableCell>
                  <TableCell>{doc.source_type}</TableCell>
                  <TableCell className="max-w-[12rem] truncate text-xs">
                    {statusLabel(doc)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-xs text-zinc-500">
                    {formatDate(doc.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <RowActions doc={doc} onChanged={onChanged} compact />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function RowActions({
  doc,
  onChanged,
  compact,
}: {
  doc: DocumentRecord;
  onChanged: () => void;
  compact?: boolean;
}) {
  return (
    <div className={`flex flex-wrap gap-2 ${compact ? "justify-end" : "mt-3"}`}>
      {doc.status === "failed" ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={async () => {
            await retryDocument(doc.id);
            onChanged();
          }}
        >
          Retry
        </Button>
      ) : null}
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
        {doc.status === "deleting" ? "Deleting…" : "Delete"}
      </Button>
    </div>
  );
}
