"use client";

import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

export function MarkdownAnswer({ text }: { text: string }) {
  return (
    <div className="prose prose-sm prose-zinc max-w-none dark:prose-invert [&_a]:pointer-events-none [&_a]:no-underline">
      <ReactMarkdown
        rehypePlugins={[rehypeSanitize]}
        components={{
          a: ({ children }) => <span>{children}</span>,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
