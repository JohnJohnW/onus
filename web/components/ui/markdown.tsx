import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

// A small, safe Markdown renderer for Onus's AI output. Handles the constrained subset the
// model is told to produce: ## headings, - bullets, 1. numbered lists, **bold**, and
// paragraphs. Builds React elements directly (no dangerouslySetInnerHTML), so text is
// always escaped. Keeps AI responses structured and scannable instead of a raw text dump.

function renderInline(text: string, keyBase: string): ReactNode[] {
  // Split on **bold** spans, keeping the delimiters.
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={`${keyBase}-${i}`} className="font-semibold text-neutral-100">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={`${keyBase}-${i}`}>{part}</span>;
  });
}

const isHeading = (s: string) => /^#{1,6}\s+/.test(s);
const isBullet = (s: string) => /^[-*]\s+/.test(s);
const isNumbered = (s: string) => /^\d+\.\s+/.test(s);

export function Markdown({ content, className }: { content: string; className?: string }) {
  const lines = (content || "").replace(/\r/g, "").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const trimmed = lines[i].trim();
    if (!trimmed) {
      i += 1;
      continue;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(trimmed);
    if (heading) {
      const level = heading[1].length;
      blocks.push(
        <p
          key={key++}
          className={cn(
            "mt-3 first:mt-0",
            level <= 2
              ? "text-sm font-semibold text-neutral-100"
              : "text-xs font-semibold uppercase tracking-wide text-neutral-400"
          )}
        >
          {renderInline(heading[2], `h${key}`)}
        </p>
      );
      i += 1;
      continue;
    }

    if (isBullet(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && isBullet(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
        i += 1;
      }
      blocks.push(
        <ul key={key++} className="my-1.5 list-disc space-y-1 pl-5 text-neutral-300">
          {items.map((it, j) => (
            <li key={j}>{renderInline(it, `b${key}-${j}`)}</li>
          ))}
        </ul>
      );
      continue;
    }

    if (isNumbered(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && isNumbered(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i += 1;
      }
      blocks.push(
        <ol key={key++} className="my-1.5 list-decimal space-y-1 pl-5 text-neutral-300">
          {items.map((it, j) => (
            <li key={j}>{renderInline(it, `o${key}-${j}`)}</li>
          ))}
        </ol>
      );
      continue;
    }

    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !isHeading(lines[i].trim()) &&
      !isBullet(lines[i].trim()) &&
      !isNumbered(lines[i].trim())
    ) {
      para.push(lines[i].trim());
      i += 1;
    }
    blocks.push(
      <p key={key++} className="my-1.5 leading-relaxed text-neutral-300 first:mt-0">
        {renderInline(para.join(" "), `p${key}`)}
      </p>
    );
  }

  return <div className={cn("text-sm", className)}>{blocks}</div>;
}
