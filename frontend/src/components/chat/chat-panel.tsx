"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";
import { Copy, RefreshCw, Square } from "lucide-react";
import { useEffect, useMemo, useState, useTransition } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import {
  createConversation,
  deleteConversation,
  getAccessToken,
  getApiBase,
  getCitation,
  listConversations,
  listDocuments,
  listMessages,
  updateConversation,
} from "@/lib/api-client/client";
import type {
  CitationRecord,
  ConversationRecord,
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

export function ChatPanel() {
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [readyDocs, setReadyDocs] = useState<DocumentRecord[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [persistedMessages, setPersistedMessages] = useState<MessageRecord[]>([]);
  const [input, setInput] = useState("");
  const [citationPreview, setCitationPreview] = useState<CitationRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const active = conversations.find((c) => c.id === activeId) || null;

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
            body: {
              conversation_id: conversationId,
            },
            headers: {
              Authorization: `Bearer ${await getAccessToken()}`,
            },
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
          headers: {
            Authorization: `Bearer ${await getAccessToken()}`,
          },
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
        // ignore refresh errors; stream already showed answer
      }
    },
    onError: (err) => setError(err.message),
  });

  const streaming = status === "streaming" || status === "submitted";

  async function refreshSidebar() {
    const [convs, docs] = await Promise.all([listConversations(), listDocuments()]);
    setConversations(convs);
    setReadyDocs(docs.filter((d) => d.status === "ready"));
  }

  useEffect(() => {
    startTransition(() => {
      void (async () => {
        try {
          await refreshSidebar();
        } catch (e) {
          setError(e instanceof Error ? e.message : "Failed to load chat");
        }
      })();
    });
  }, []);

  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      setPersistedMessages([]);
      return;
    }
    void (async () => {
      try {
        const [conv, rows] = await Promise.all([
          listConversations().then((all) => all.find((c) => c.id === activeId)),
          listMessages(activeId),
        ]);
        if (conv) {
          setSelectedDocIds(conv.selected_document_ids || []);
        }
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
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load messages");
      }
    })();
  }, [activeId, setMessages]);

  async function handleNewChat() {
    setError(null);
    const conv = await createConversation({
      selected_document_ids: selectedDocIds,
    });
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
  }

  async function toggleDoc(docId: string) {
    const next = selectedDocIds.includes(docId)
      ? selectedDocIds.filter((id) => id !== docId)
      : [...selectedDocIds, docId];
    setSelectedDocIds(next);
    if (activeId) {
      const updated = await updateConversation(activeId, {
        selected_document_ids: next,
      });
      setConversations((prev) =>
        prev.map((c) => (c.id === updated.id ? updated : c)),
      );
    }
  }

  async function handleSend() {
    if (!input.trim() || streaming) return;
    setError(null);
    let conversationId = activeId;
    if (!conversationId) {
      const conv = await createConversation({
        selected_document_ids: selectedDocIds,
      });
      setConversations((prev) => [conv, ...prev]);
      conversationId = conv.id;
      setActiveId(conv.id);
    }
    if (!selectedDocIds.length) {
      setError("Select at least one ready document");
      return;
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

  async function handleCopy(text: string) {
    await navigator.clipboard.writeText(text);
  }

  async function openCitation(citation: CitationRecord) {
    try {
      const fresh = await getCitation(citation.id);
      setCitationPreview(fresh);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Citation unavailable");
    }
  }

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
    <div className="grid min-h-[70vh] gap-4 lg:grid-cols-[220px_1fr_220px]">
      <aside className="flex flex-col gap-2 border-r border-zinc-200 pr-3">
        <Button type="button" onClick={() => void handleNewChat()} disabled={pending}>
          New chat
        </Button>
        <ScrollArea className="h-[60vh]">
          <ul className="space-y-1 text-sm">
            {conversations.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  className={`w-full rounded px-2 py-1.5 text-left hover:bg-zinc-100 ${
                    c.id === activeId ? "bg-zinc-100 font-medium" : ""
                  }`}
                  onClick={() => setActiveId(c.id)}
                >
                  {c.title}
                </button>
              </li>
            ))}
          </ul>
        </ScrollArea>
        {activeId ? (
          <Button
            type="button"
            variant="ghost"
            className="text-xs text-zinc-500"
            onClick={() =>
              void deleteConversation(activeId).then(() => {
                setConversations((prev) => prev.filter((c) => c.id !== activeId));
                setActiveId(null);
              })
            }
          >
            Delete chat
          </Button>
        ) : null}
      </aside>

      <section className="flex min-w-0 flex-col gap-3">
        <div className="flex flex-wrap gap-3 text-sm">
          {readyDocs.length === 0 ? (
            <p className="text-zinc-500">No ready documents yet. Ingest files first.</p>
          ) : (
            readyDocs.map((doc) => (
              <label key={doc.id} className="flex items-center gap-2">
                <Checkbox
                  checked={selectedDocIds.includes(doc.id)}
                  onCheckedChange={() => void toggleDoc(doc.id)}
                />
                <span className="truncate max-w-[12rem]" title={doc.filename}>
                  {doc.filename}
                </span>
              </label>
            ))
          )}
        </div>

        <ScrollArea className="h-[48vh] rounded border border-zinc-200 bg-white p-3">
          <div className="space-y-4">
            {messages.map((m) => {
              const text = messageText(m);
              const cites = citationsByAssistant.get(m.id) || [];
              return (
                <div
                  key={m.id}
                  className={`flex flex-col gap-1 ${
                    m.role === "user" ? "items-end" : "items-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                      m.role === "user"
                        ? "bg-zinc-900 text-white"
                        : "bg-zinc-100 text-zinc-900"
                    }`}
                  >
                    {text || (streaming && m.role === "assistant" ? "…" : "")}
                  </div>
                  {m.role === "assistant" && text ? (
                    <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 hover:text-zinc-800"
                        onClick={() => void handleCopy(text)}
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
        </ScrollArea>

        {error ? <p className="text-sm text-red-600">{error}</p> : null}

        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your selected documents…"
            className="min-h-[72px]"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
          />
          <div className="flex flex-col gap-2">
            {streaming ? (
              <Button type="button" variant="outline" onClick={() => stop()}>
                <Square className="size-4" />
              </Button>
            ) : (
              <Button type="button" onClick={() => void handleSend()}>
                Send
              </Button>
            )}
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
        {active ? (
          <p className="mt-6 text-xs text-zinc-400">Conversation {active.id.slice(0, 8)}…</p>
        ) : null}
      </aside>
    </div>
  );
}
