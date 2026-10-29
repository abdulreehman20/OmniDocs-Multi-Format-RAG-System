"use client";

import { authClient } from "@/lib/auth/client";

import type {
  CitationRecord,
  ConversationRecord,
  DocumentRecord,
  MeRecord,
  MessageRecord,
  UploadInitResponse,
  UploadLimits,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function getApiBase(): string {
  return API_BASE;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `API error ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export async function getAccessToken(): Promise<string> {
  const { data, error } = await authClient.token();
  if (error || !data?.token) {
    throw new ApiError(401, error?.message || "Unable to obtain access token");
  }
  return data.token;
}

async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  retried = false,
): Promise<T> {
  const token = await getAccessToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init.headers || {}),
    },
  });

  if (response.status === 401 && !retried) {
    return apiFetch<T>(path, init, true);
  }

  if (!response.ok) {
    let detail: unknown = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? body;
    } catch {
      // ignore
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function getLimits() {
  return apiFetch<UploadLimits>("/api/v1/limits");
}

export function listDocuments() {
  return apiFetch<DocumentRecord[]>("/api/v1/documents");
}

export function initUpload(input: {
  filename: string;
  mime_type: string;
  byte_size: number;
  idempotency_key: string;
}) {
  return apiFetch<UploadInitResponse>("/api/v1/uploads/init", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function completeUpload(documentId: string) {
  return apiFetch<DocumentRecord>(`/api/v1/documents/${documentId}/complete`, {
    method: "POST",
  });
}

export function downloadDocument(documentId: string) {
  return apiFetch<{ document_id: string; filename: string; download_url: string }>(
    `/api/v1/documents/${documentId}/download`,
  );
}

export function deleteDocument(documentId: string) {
  return apiFetch<DocumentRecord>(`/api/v1/documents/${documentId}/delete`, {
    method: "POST",
  });
}

export function retryDocument(documentId: string) {
  return apiFetch<DocumentRecord>(`/api/v1/documents/${documentId}/retry`, {
    method: "POST",
  });
}

export function listConversations() {
  return apiFetch<ConversationRecord[]>("/api/v1/conversations");
}

export function createConversation(input?: {
  title?: string;
  selected_document_ids?: string[];
}) {
  return apiFetch<ConversationRecord>("/api/v1/conversations", {
    method: "POST",
    body: JSON.stringify(input || {}),
  });
}

export function getConversation(conversationId: string) {
  return apiFetch<ConversationRecord>(`/api/v1/conversations/${conversationId}`);
}

export function updateConversation(
  conversationId: string,
  input: {
    title?: string;
    selected_document_ids?: string[];
    archived?: boolean;
  },
) {
  return apiFetch<ConversationRecord>(`/api/v1/conversations/${conversationId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteConversation(conversationId: string) {
  return apiFetch<ConversationRecord>(`/api/v1/conversations/${conversationId}`, {
    method: "DELETE",
  });
}

export function listMessages(conversationId: string) {
  return apiFetch<MessageRecord[]>(`/api/v1/conversations/${conversationId}/messages`);
}

export function getCitation(citationId: string) {
  return apiFetch<CitationRecord>(`/api/v1/citations/${citationId}`);
}

export function getMe() {
  return apiFetch<MeRecord>("/api/v1/me");
}

export function updateMe(input: {
  display_name?: string | null;
  preferences?: Record<string, unknown>;
}) {
  return apiFetch<MeRecord>("/api/v1/me", {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function putFileToPresignedUrl(
  putUrl: string,
  file: File,
  onProgress?: (pct: number) => void,
  signal?: AbortSignal,
): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", putUrl);
    xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("Upload network error"));
    xhr.onabort = () => reject(new DOMException("Upload cancelled", "AbortError"));
    if (signal) {
      if (signal.aborted) {
        xhr.abort();
        return;
      }
      signal.addEventListener("abort", () => xhr.abort(), { once: true });
    }
    xhr.send(file);
  });
}
