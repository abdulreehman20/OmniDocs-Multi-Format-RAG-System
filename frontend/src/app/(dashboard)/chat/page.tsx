import { Suspense } from "react";

import { ChatPanel } from "@/components/chat/chat-panel";

export default function ChatPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Chat</h1>
        <p className="text-sm text-zinc-500">
          Ask questions over ready documents with grounded, cited answers.
        </p>
      </div>
      <Suspense
        fallback={<p className="text-sm text-zinc-500">Loading chat…</p>}
      >
        <ChatPanel />
      </Suspense>
    </div>
  );
}
