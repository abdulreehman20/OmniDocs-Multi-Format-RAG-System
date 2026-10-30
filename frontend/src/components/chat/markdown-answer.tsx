"use client";

import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";

const CITE_RE = /\[(S\d+)\]/g;

/** Repair pipe-tables the model jammed onto one line so GFM can parse them. */
function normalizeMarkdownTables(text: string): string {
  // Common jam: |a|b||---|---||c|d|
  if (!text.includes("||")) return text;
  return text.replace(/\|\|/g, "|\n|");
}

function withCitationButtons(
  children: ReactNode,
  onCitationClick?: (label: string) => void,
): ReactNode {
  if (!onCitationClick) return children;

  const walk = (node: ReactNode): ReactNode => {
    if (typeof node === "string") {
      const parts: ReactNode[] = [];
      let last = 0;
      let match: RegExpExecArray | null;
      const re = new RegExp(CITE_RE.source, "g");
      while ((match = re.exec(node)) !== null) {
        if (match.index > last) parts.push(node.slice(last, match.index));
        const label = match[1]!;
        parts.push(
          <button
            key={`${label}-${match.index}`}
            type="button"
            className="mx-0.5 inline rounded border border-zinc-300 bg-white px-1 py-0.5 text-xs font-medium text-zinc-700 hover:bg-zinc-50"
            onClick={() => onCitationClick(label)}
          >
            [{label}]
          </button>,
        );
        last = match.index + match[0].length;
      }
      if (last === 0) return node;
      if (last < node.length) parts.push(node.slice(last));
      return parts;
    }
    if (Array.isArray(node)) return node.map((child, i) => <span key={i}>{walk(child)}</span>);
    return node;
  };

  return walk(children);
}

export function MarkdownAnswer({
  text,
  onCitationClick,
}: {
  text: string;
  onCitationClick?: (label: string) => void;
}) {
  return (
    <div className="prose prose-sm prose-zinc max-w-none dark:prose-invert [&_a]:pointer-events-none [&_a]:no-underline [&_table]:block [&_table]:w-full [&_table]:overflow-x-auto">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          a: ({ children }) => <span>{children}</span>,
          p: ({ children }) => <p>{withCitationButtons(children, onCitationClick)}</p>,
          li: ({ children }) => <li>{withCitationButtons(children, onCitationClick)}</li>,
          td: ({ children }) => <td>{withCitationButtons(children, onCitationClick)}</td>,
          th: ({ children }) => <th>{withCitationButtons(children, onCitationClick)}</th>,
        }}
      >
        {normalizeMarkdownTables(text)}
      </ReactMarkdown>
    </div>
  );
}
