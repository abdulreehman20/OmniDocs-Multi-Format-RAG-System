"use client";

import {
  FileText,
  MessageSquare,
  PanelLeft,
  Plus,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { SignOutButton } from "@/components/layout/sign-out-button";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { createConversation, listConversations } from "@/lib/api-client/client";
import type { ConversationRecord } from "@/lib/api-client/types";

function NavLinks({
  conversations,
  activeConversationId,
  onNavigate,
}: {
  conversations: ConversationRecord[];
  activeConversationId: string | null;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();

  const linkClass = (active: boolean) =>
    `flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
      active ? "bg-zinc-200 font-medium text-zinc-900" : "text-zinc-700 hover:bg-zinc-100"
    }`;

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="space-y-1">
        <p className="px-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
          Workspace
        </p>
        <Link
          href="/documents"
          className={linkClass(pathname.startsWith("/documents"))}
          onClick={onNavigate}
        >
          <FileText className="size-4 shrink-0" aria-hidden />
          Documents
        </Link>
        <Link
          href="/chat"
          className={linkClass(pathname.startsWith("/chat") && !activeConversationId)}
          onClick={onNavigate}
        >
          <MessageSquare className="size-4 shrink-0" aria-hidden />
          Chat
        </Link>
        <Link
          href="/settings"
          className={linkClass(pathname.startsWith("/settings"))}
          onClick={onNavigate}
        >
          <Settings className="size-4 shrink-0" aria-hidden />
          Settings
        </Link>
      </div>

      <div className="min-h-0 flex-1 space-y-1">
        <p className="px-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
          Conversations
        </p>
        <ScrollArea className="h-[min(50vh,24rem)]">
          <ul className="space-y-0.5 pr-2">
            {conversations.length === 0 ? (
              <li className="px-2 py-1 text-xs text-zinc-500">No chats yet</li>
            ) : (
              conversations.map((c) => (
                <li key={c.id}>
                  <Link
                    href={`/chat?c=${encodeURIComponent(c.id)}`}
                    className={linkClass(activeConversationId === c.id)}
                    onClick={onNavigate}
                    title={c.title}
                  >
                    <span className="truncate">{c.title || "Untitled"}</span>
                  </Link>
                </li>
              ))
            )}
          </ul>
        </ScrollArea>
      </div>
    </div>
  );
}

export function DashboardNav({ userLabel }: { userLabel?: string | null }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeConversationId = searchParams.get("c");
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const rows = await listConversations();
      setConversations(rows);
    } catch {
      // ignore; shell still usable
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, activeConversationId]);

  useEffect(() => {
    const onChanged = () => void refresh();
    window.addEventListener("rag:conversations-changed", onChanged);
    return () => window.removeEventListener("rag:conversations-changed", onChanged);
  }, [refresh]);

  async function handleNewChat() {
    setCreating(true);
    try {
      const conv = await createConversation();
      setConversations((prev) => [conv, ...prev.filter((c) => c.id !== conv.id)]);
      setMobileOpen(false);
      router.push(`/chat?c=${encodeURIComponent(conv.id)}`);
    } finally {
      setCreating(false);
    }
  }

  const sidebarBody = (
    <>
      <div className="mb-4 flex items-center justify-between gap-2">
        <Link href="/" className="text-sm font-semibold tracking-tight text-zinc-900">
          Omni-RAG
        </Link>
      </div>
      <Button
        type="button"
        className="mb-4 w-full justify-start gap-2"
        onClick={() => void handleNewChat()}
        disabled={creating}
        aria-label="New chat"
      >
        <Plus className="size-4" aria-hidden />
        New Chat
      </Button>
      <NavLinks
        conversations={conversations}
        activeConversationId={activeConversationId}
        onNavigate={() => setMobileOpen(false)}
      />
      <div className="mt-auto space-y-2 border-t border-zinc-200 pt-3 text-sm text-zinc-600">
        {userLabel ? <p className="truncate px-1 text-xs">{userLabel}</p> : null}
        <SignOutButton />
      </div>
    </>
  );

  return (
    <>
      <aside
        className="hidden w-64 shrink-0 flex-col border-r border-zinc-200 bg-white p-4 md:flex"
        aria-label="Dashboard navigation"
      >
        <div className="flex h-full flex-col gap-1">{sidebarBody}</div>
      </aside>

      <div className="flex items-center gap-2 border-b border-zinc-200 bg-white px-3 py-2 md:hidden">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Open navigation"
          onClick={() => setMobileOpen(true)}
        >
          <PanelLeft className="size-4" />
        </Button>
        <span className="text-sm font-medium">rag-basic</span>
        <Button
          type="button"
          size="sm"
          className="ml-auto"
          onClick={() => void handleNewChat()}
          disabled={creating}
        >
          New Chat
        </Button>
      </div>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-72 p-4">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <div className="flex h-full flex-col">{sidebarBody}</div>
        </SheetContent>
      </Sheet>
    </>
  );
}
