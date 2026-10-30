"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { Copy, RefreshCw, Square } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { MarkdownAnswer } from "@/components/chat/markdown-answer";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  createConversation,
  deleteConversation,
  fetchWithAuth,
  getApiBase,
  getCitation,
  getConversation,
  listDocuments,
  listMessages,
  updateConversation,
} from "@/lib/api-client/client";
import type {
  CitationRecord,
  DocumentRecord,
  MessageRecord,
} from "@/lib/api-client/types";

function messageText(message: UIMessage): string {
  return message.parts
    .filter((p): p is { type: "text"; text: string } => p.type === "text")
    .map((p) => p.text)
    .join("");
}

/** Prefer human-facing locator fields; drop ephemeral temp `source` paths. */
function locatorRows(locator: Record<string, unknown>): { label: string; value: string }[] {
  const rows: { label: string; value: string }[] = [];
  const prefer = [
    "kind",
    "page",
    "page_start",
    "page_end",
    "row_start",
    "row_end",
    "heading",
    "sheet",
    "unit_index",
  ];
  const seen = new Set<string>();
  for (const key of prefer) {
    if (!(key in (locator || {}))) continue;
    const raw = locator[key];
    if (raw == null || raw === "") continue;
    seen.add(key);
    rows.push({ label: key.replaceAll("_", " "), value: String(raw) });
  }
  for (const [key, raw] of Object.entries(locator || {})) {
    if (seen.has(key) || key === "source") continue;
    if (raw == null || raw === "") continue;
    const value = String(raw);
    // Skip absolute temp paths from local parse staging.
    if (/[\\/]Temp[\\/]/i.test(value) || /^[A-Za-z]:\\/.test(value)) continue;
    rows.push({ label: key.replaceAll("_", " "), value });
  }
  return rows;
}

function formatDuration(ms: number | null | undefined): string | null {
  if (ms == null || ms < 0) return null;
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function notifyConversationsChanged() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("rag:conversations-changed"));
  }
}

export function ChatPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeId = searchParams.get("c");

  const [readyDocs, setReadyDocs] = useState<DocumentRecord[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [persistedMessages, setPersistedMessages] = useState<MessageRecord[]>([]);
  const [input, setInput] = useState("");
  const [citationPreview, setCitationPreview] = useState<CitationRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ragProgress, setRagProgress] = useState<string | null>(null);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [pendingSend, setPendingSend] = useState<{
    conversationId: string;
    text: string;
    selectedDocumentIds: string[];
  } | null>(null);

  const transport = useMemo(() => {
    return new DefaultChatTransport({
      api: `${getApiBase()}/api/v1/chat`,
      // Same 401→fresh-JWT retry as apiFetch; chat previously had none.
      fetch: fetchWithAuth,
      prepareSendMessagesRequest: async ({ messages, trigger, body }) => {
        const lastUser = [...messages].reverse().find((m) => m.role === "user");
        const text = lastUser ? messageText(lastUser) : "";
        const conversationId =
          (body as { conversation_id?: string } | undefined)?.conversation_id ||
          activeId;
        const docs =
          (body as { selected_document_ids?: string[] } | undefined)
            ?.selected_document_ids || selectedDocIds;

        if (trigger === "regenerate-message") {
          return {
            api: `${getApiBase()}/api/v1/chat/regenerate`,
            body: { conversation_id: conversationId },
          };
        }

        return {
          api: `${getApiBase()}/api/v1/chat`,
          body: {
            conversation_id: conversationId,
            message: text,
            selected_document_ids: docs,
            idempotency_key: crypto.randomUUID(),
          },
        };
      },
    });
  }, [activeId, selectedDocIds]);

  const { messages, sendMessage, regenerate, stop, status, setMessages } = useChat({
    id: activeId || "empty",
    transport,
    onFinish: async () => {
      setRagProgress(null);
      notifyConversationsChanged();
      if (!activeId) return;
      try {
        const rows = await listMessages(activeId);
        setPersistedMessages(rows);
      } catch {
        // stream already showed answer
      }
    },
    onError: (err) => {
      setRagProgress(null);
      const raw = err.message || "Chat request failed";
      try {
        const parsed = JSON.parse(raw) as { detail?: unknown };
        if (typeof parsed.detail === "string") {
          setError(parsed.detail);
          return;
        }
      } catch {
        // not JSON
      }
      setError(raw);
    },
  });

  const streaming = status === "streaming" || status === "submitted";

  // Drop the banner as soon as the transport leaves streaming (finish / error / stop).
  useEffect(() => {
    if (!streaming) setRagProgress(null);
  }, [streaming]);

  useEffect(() => {
    void listDocuments()
      .then((docs) => setReadyDocs(docs.filter((d) => d.status === "ready")))
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load documents"),
      );
  }, []);

  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      setPersistedMessages([]);
      setSelectedDocIds([]);
      setRagProgress(null);
      return;
    }
    setLoadingMessages(true);
    void (async () => {
      try {
        const [rows, conv] = await Promise.all([
          listMessages(activeId),
          getConversation(activeId),
        ]);
        setPersistedMessages(rows);
        setMessages(
          rows
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map(
              (m): UIMessage => ({
                id: m.id,
                role: m.role as "user" | "assistant",
                parts: [{ type: "text", text: m.content }],
              }),
            ),
        );
        setSelectedDocIds(conv.selected_document_ids || []);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load messages");
      } finally {
        setLoadingMessages(false);
      }
    })();
  }, [activeId, setMessages]);

  // Flush message after create→navigate (avoids useChat id change aborting the stream).
  useEffect(() => {
    if (!activeId || !pendingSend || loadingMessages || streaming) return;
    if (pendingSend.conversationId !== activeId) return;
    const { text, selectedDocumentIds: docs } = pendingSend;
    setPendingSend(null);
    if (docs.length) setSelectedDocIds(docs);
    setRagProgress("Embedding question…");
    void sendMessage(
      { text },
      {
        body: {
          conversation_id: activeId,
          selected_document_ids: docs,
        },
      },
    );
  }, [activeId, pendingSend, loadingMessages, streaming, sendMessage]);

  // Title is set server-side when the turn begins — refresh sidebar early.
  useEffect(() => {
    if (streaming) notifyConversationsChanged();
  }, [streaming]);

  // Poll Inngest job progress while streaming.
  useEffect(() => {
    if (!streaming || !activeId) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const rows = await listMessages(activeId);
        if (cancelled) return;
        const assistant = [...rows].reverse().find((m) => m.role === "assistant");
        // Soft-clear: DB already finalized even if SSE finish is late.
        if (
          assistant &&
          (assistant.status === "completed" ||
            assistant.status === "partial" ||
            assistant.status === "failed")
        ) {
          setRagProgress(null);
        } else if (assistant?.progress_label) {
          setRagProgress(assistant.progress_label);
        }
        setPersistedMessages(rows);
      } catch {
        // ignore transient poll errors
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 400);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [streaming, activeId]);

  async function toggleDoc(docId: string) {
    const next = selectedDocIds.includes(docId)
      ? selectedDocIds.filter((id) => id !== docId)
      : [...selectedDocIds, docId];
    setSelectedDocIds(next);
    if (activeId) {
      await updateConversation(activeId, { selected_document_ids: next });
    }
  }

  async function handleSend() {
    if (!input.trim() || streaming) return;
    setError(null);
    if (!selectedDocIds.length) {
      setError("Select at least one ready document");
      return;
    }
    // Creating a conversation changes useChat `id` (activeId) mid-flight and
    // aborts the stream — navigate first, then send once the URL has settled.
    if (!activeId) {
      try {
        const conv = await createConversation({
          selected_document_ids: selectedDocIds,
        });
        const text = input.trim();
        setInput("");
        // Keep loading=true until the conversation hydrate effect finishes so
        // pending send does not race setMessages([]) and wipe the optimistic UI.
        setLoadingMessages(true);
        setPendingSend({
          conversationId: conv.id,
          text,
          selectedDocumentIds: selectedDocIds,
        });
        notifyConversationsChanged();
        router.replace(`/chat?c=${encodeURIComponent(conv.id)}`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to create chat");
      }
      return;
    }
    const text = input.trim();
    setInput("");
    setRagProgress("Embedding question…");
    await sendMessage(
      { text },
      {
        body: {
          conversation_id: activeId,
          selected_document_ids: selectedDocIds,
        },
      },
    );
  }

  async function openCitation(citation: CitationRecord) {
    try {
      const fresh = await getCitation(citation.id);
      setCitationPreview(fresh);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Citation unavailable");
    }
  }

  function openCitationByLabel(label: string, cites: CitationRecord[]) {
    const hit = cites.find((c) => c.label === label || `[${c.label}]` === label);
    if (hit) void openCitation(hit);
  }

  const latencyById = useMemo(() => {
    const map = new Map<string, number | null>();
    for (const m of persistedMessages) {
      if (m.role === "assistant") map.set(m.id, m.latency_ms);
    }
    return map;
  }, [persistedMessages]);

  const citationsByAssistant = useMemo(() => {
    const map = new Map<string, CitationRecord[]>();
    for (const m of persistedMessages) {
      if (m.role === "assistant" && m.citations?.length) {
        map.set(m.id, m.citations);
      }
    }
    return map;
  }, [persistedMessages]);

  // Latest assistant citations for the Source panel (by stream id or DB id).
  const latestCitations = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i]!;
      if (m.role !== "assistant") continue;
      const byId = citationsByAssistant.get(m.id);
      if (byId?.length) return byId;
    }
    for (let i = persistedMessages.length - 1; i >= 0; i--) {
      const m = persistedMessages[i]!;
      if (m.role === "assistant" && m.citations?.length) return m.citations;
    }
    return [] as CitationRecord[];
  }, [messages, citationsByAssistant, persistedMessages]);

  // Keep Source panel in sync with the latest answer's citations.
  useEffect(() => {
    if (!latestCitations.length) {
      setCitationPreview(null);
      return;
    }
    setCitationPreview((prev) => {
      if (prev && latestCitations.some((c) => c.id === prev.id)) return prev;
      return latestCitations[0]!;
    });
  }, [latestCitations]);

  return (
    <div className="grid min-h-[70vh] gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,240px)]">
      <section className="flex min-w-0 flex-col gap-4">
        <div className="flex flex-wrap gap-3 rounded-lg border border-zinc-200 bg-white p-3 text-sm">
          {readyDocs.length === 0 ? (
            <p className="text-zinc-500">
              No ready documents yet. Upload and wait for ingestion on Documents.
            </p>
          ) : (
            readyDocs.map((doc) => (
              <label key={doc.id} className="flex items-center gap-2">
                <Checkbox
                  checked={selectedDocIds.includes(doc.id)}
                  onCheckedChange={() => void toggleDoc(doc.id)}
                />
                <span className="max-w-[12rem] truncate" title={doc.filename}>
                  {doc.filename}
                </span>
              </label>
            ))
          )}
        </div>

        {ragProgress && streaming ? (
          <p className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-600">
            {ragProgress}
          </p>
        ) : null}

        <ScrollArea className="h-[48vh] rounded-lg border border-zinc-200 bg-white p-4">
          {loadingMessages ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-3/4" />
              <Skeleton className="h-24 w-full" />
            </div>
          ) : messages.length === 0 ? (
            <p className="py-10 text-center text-sm text-zinc-500">
              {activeId
                ? "Ask a question about your selected documents."
                : "Select New Chat or a conversation from the sidebar to begin."}
            </p>
          ) : (
            <div className="space-y-4">
              {messages.map((m) => {
                const text = messageText(m);
                const cites = citationsByAssistant.get(m.id) || [];
                const duration = formatDuration(latencyById.get(m.id));
                return (
                  <div
                    key={m.id}
                    className={`flex flex-col gap-1 ${
                      m.role === "user" ? "items-end" : "items-start"
                    }`}
                  >
                    <div
                      className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                        m.role === "user"
                          ? "whitespace-pre-wrap bg-zinc-900 text-white"
                          : "bg-zinc-100 text-zinc-900"
                      }`}
                    >
                      {m.role === "assistant" ? (
                        text ? (
                          <MarkdownAnswer
                            text={text}
                            onCitationClick={(label) => openCitationByLabel(label, cites)}
                          />
                        ) : streaming ? (
                          ragProgress || "…"
                        ) : null
                      ) : (
                        text
                      )}
                    </div>
                    {m.role === "assistant" && text ? (
                      <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                        <button
                          type="button"
                          className="inline-flex items-center gap-1 hover:text-zinc-800"
                          onClick={() => void navigator.clipboard.writeText(text)}
                        >
                          <Copy className="size-3" /> Copy
                        </button>
                        <button
                          type="button"
                          className="inline-flex items-center gap-1 hover:text-zinc-800"
                          disabled={streaming}
                          onClick={() => void regenerate()}
                        >
                          <RefreshCw className="size-3" /> Regenerate
                        </button>
                        {duration ? <span>{duration}</span> : null}
                        {cites.map((c) => (
                          <button
                            key={c.id}
                            type="button"
                            className="rounded border border-zinc-300 px-1.5 py-0.5 hover:bg-zinc-50"
                            onClick={() => void openCitation(c)}
                          >
                            [{c.label}] {c.filename}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}

        <div className="flex gap-3">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your selected documents…"
            className="min-h-[72px]"
            disabled={!readyDocs.length}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
          />
          <div className="flex flex-col gap-2">
            {streaming ? (
              <Button type="button" variant="outline" onClick={() => stop()} aria-label="Stop">
                <Square className="size-4" />
              </Button>
            ) : (
              <Button type="button" onClick={() => void handleSend()}>
                Send
              </Button>
            )}
            {activeId ? (
              <Button
                type="button"
                variant="ghost"
                className="text-xs text-zinc-500"
                onClick={() =>
                  void deleteConversation(activeId).then(() => {
                    notifyConversationsChanged();
                    router.push("/chat");
                  })
                }
              >
                Delete
              </Button>
            ) : null}
          </div>
        </div>
      </section>

      <aside className="min-w-0 overflow-hidden rounded-lg border border-zinc-200 bg-white p-4 text-sm">
        <h2 className="mb-3 font-medium">Source</h2>
        {latestCitations.length ? (
          <ul className="mb-4 space-y-1">
            {latestCitations.map((c) => (
              <li key={c.id} className="min-w-0">
                <button
                  type="button"
                  title={`[${c.label}] ${c.filename}`}
                  className={`flex w-full min-w-0 items-center gap-1 rounded border px-2 py-1.5 text-left text-xs hover:bg-zinc-50 ${
                    citationPreview?.id === c.id
                      ? "border-zinc-900 bg-zinc-50 font-medium"
                      : "border-zinc-200"
                  }`}
                  onClick={() => void openCitation(c)}
                >
                  <span className="shrink-0">[{c.label}]</span>
                  <span className="truncate">{c.filename}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mb-4 text-zinc-500">
            Citations appear here after an answer finishes.
          </p>
        )}
        {citationPreview ? (
          <div className="min-w-0 space-y-2 overflow-hidden border-t border-zinc-100 pt-3 text-zinc-700">
            <p className="wrap-break-word font-medium">
              [{citationPreview.label}] {citationPreview.filename}
            </p>
            {locatorRows(citationPreview.locator).length ? (
              <dl className="space-y-1 text-xs text-zinc-500">
                {locatorRows(citationPreview.locator).map((row) => (
                  <div key={row.label} className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-2">
                    <dt className="shrink-0 capitalize text-zinc-400">{row.label}</dt>
                    <dd className="min-w-0 wrap-anywhere">{row.value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
            {citationPreview.excerpt ? (
              <div className="max-h-64 overflow-y-auto overflow-x-hidden rounded bg-zinc-50 p-2 text-xs">
                <p className="wrap-anywhere whitespace-pre-wrap">
                  {citationPreview.excerpt}
                </p>
              </div>
            ) : null}
          </div>
        ) : null}
        {activeId ? (
          <p className="mt-6 break-all text-xs text-zinc-400">Conversation {activeId}</p>
        ) : null}
      </aside>
    </div>
  );
}
