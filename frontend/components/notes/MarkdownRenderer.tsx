/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

/**
 * MarkdownRenderer — renders a markdown string with GitHub-Flavored Markdown
 * support via react-markdown + remark-gfm.
 *
 * Applies Tailwind Typography `prose prose-invert prose-sm` classes for
 * consistent dark-theme styling inside note cards.
 */

"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  /** Raw markdown string to render. */
  content: string;
  /** Additional CSS class names applied to the wrapper div. */
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: Props) {
  return (
    <div
      className={[
        "prose prose-invert prose-sm max-w-none",
        // Override some prose defaults to fit the dark card style
        "prose-p:my-1 prose-p:text-foreground prose-p:leading-relaxed",
        "prose-headings:text-foreground prose-headings:font-semibold",
        "prose-strong:text-foreground",
        "prose-em:text-muted-foreground",
        "prose-code:text-[color:var(--code-fg)] prose-code:bg-secondary/60 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs",
        "prose-pre:bg-background prose-pre:border prose-pre:border-border prose-pre:rounded-lg",
        "prose-blockquote:border-l-zinc-500 prose-blockquote:text-muted-foreground",
        "prose-ul:text-foreground prose-ol:text-foreground",
        "prose-li:my-0.5",
        "prose-a:text-primary prose-a:no-underline hover:prose-a:underline",
        "prose-hr:border-border",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
