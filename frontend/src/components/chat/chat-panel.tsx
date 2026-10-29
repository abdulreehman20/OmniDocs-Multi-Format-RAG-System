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
  getAccessToken,
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

function formatLocator(locator: Record<string, unknown>): string {
  const entries = Object.entries(locator || {});
  if (!entries.length) return "";
  return entries.map(([k, v]) => `${k}: ${String(v)}`).join(" · ");
}

function formatDuration(ms: number | null | undefined): string | null {
  if (ms == null || ms < 0) return null;
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
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
  const [loadingMessages, setLoadingMessages] = useState(false);

  const transport = useMemo(() => {
    return new DefaultChatTransport({
      api: `${getApiBase()}/api/v1/chat`,
      headers: async () => {
        const token = await getAccessToken();
        return { Authorization: `Bearer ${token}` };
      },
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
            headers: { Authorization: `Bearer ${await getAccessToken()}` },
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
          headers: { Authorization: `Bearer ${await getAccessToken()}` },
        };
      },
    });
  }, [activeId, selectedDocIds]);

  const { messages, sendMessage, regenerate, stop, status, setMessages } = useChat({
    id: activeId || "empty",
    transport,
    onFinish: async () => {
      if (!activeId) return;
      try {
        const rows = await listMessages(activeId);
        setPersistedMessages(rows);
      } catch {
        // stream already showed answer
      }
    },
    onError: (err) => setError(err.message),
  });

  const streaming = status === "streaming" || status === "submitted";

  useEffect(() => {
    void listDocuments()
      .then((docs) => setReadyDocs(docs.filter((d) => d.status === "ready")))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load documents"));
  }, []);

  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      setPersistedMessages([]);
      setSelectedDocIds([]);
      return;
    }
    setLoadingMessages(true);
    void (async () => {
      try {
        const rows = await listMessages(activeId);
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
        const conv = await getConversation(activeId);
        setSelectedDocIds(conv.selected_document_ids || []);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load messages");
      } finally {
        setLoadingMessages(false);
      }
    })();
  }, [activeId, setMessages]);

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
    let conversationId = activeId;
    if (!conversationId) {
      const conv = await createConversation({
        selected_document_ids: selectedDocIds,
      });
      conversationId = conv.id;
      router.replace(`/chat?c=${encodeURIComponent(conv.id)}`);
    }
    const text = input.trim();
    setInput("");
    await sendMessage(
      { text },
      {
        body: {
          conversation_id: conversationId,
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

  return (
    <div className="grid min-h-[70vh] gap-4 lg:grid-cols-[1fr_220px]">
      <section className="flex min-w-0 flex-col gap-3">
        <div className="flex flex-wrap gap-3 text-sm">
          {readyDocs.length === 0 ? (
            <p className="rounded-lg border border-dashed bg-zinc-50 px-3 py-2 text-zinc-500">
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

        <ScrollArea className="h-[48vh] rounded border border-zinc-200 bg-white p-3">
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
                          <MarkdownAnswer text={text} />
                        ) : streaming ? (
                          "…"
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

        <div className="flex gap-2">
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

      <aside className="border-l border-zinc-200 pl-3 text-sm">
        <h2 className="mb-2 font-medium">Source</h2>
        {citationPreview ? (
          <div className="space-y-2 text-zinc-700">
            <p className="font-medium">
              [{citationPreview.label}] {citationPreview.filename}
            </p>
            <p className="text-xs text-zinc-500">
              {formatLocator(citationPreview.locator)}
            </p>
            {citationPreview.excerpt ? (
              <p className="whitespace-pre-wrap rounded bg-zinc-50 p-2 text-xs">
                {citationPreview.excerpt}
              </p>
            ) : null}
          </div>
        ) : (
          <p className="text-zinc-500">Open a citation to preview the locator.</p>
        )}
      </aside>
    </div>
  );
}
