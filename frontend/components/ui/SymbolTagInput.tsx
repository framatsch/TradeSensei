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

"use client";

import React, { useState, KeyboardEvent, useRef } from "react";
import * as Popover from "@radix-ui/react-popover";
import { HelpCircle, X } from "lucide-react";

interface SymbolTagInputProps {
  id?: string;
  included: string[];
  excluded: string[];
  onChange: (included: string[], excluded: string[]) => void;
  className?: string;
  placeholder?: string;
}

export function SymbolTagInput({
  id,
  included,
  excluded,
  onChange,
  className = "",
  placeholder = "Filter symbols...",
}: SymbolTagInputProps) {
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTags(inputValue);
    } else if (e.key === "Backspace" && inputValue === "") {
      if (excluded.length > 0) {
        onChange(included, excluded.slice(0, -1));
      } else if (included.length > 0) {
        onChange(included.slice(0, -1), excluded);
      }
    }
  };

  const addTags = (value: string) => {
    const rawTags = value
      .split(",")
      .map((t) => t.trim().toUpperCase())
      .filter((t) => t.length > 0);

    if (rawTags.length === 0) return;

    const newIncluded = [...included];
    const newExcluded = [...excluded];

    rawTags.forEach((tag) => {
      let isExcluded = false;
      let cleanTag = tag;

      if (tag.startsWith("!")) {
        isExcluded = true;
        cleanTag = tag.substring(1).trim();
      }

      if (!cleanTag) return;

      if (isExcluded) {
        if (!newExcluded.includes(cleanTag) && !newIncluded.includes(cleanTag)) {
          newExcluded.push(cleanTag);
        }
      } else {
        if (!newIncluded.includes(cleanTag) && !newExcluded.includes(cleanTag)) {
          newIncluded.push(cleanTag);
        }
      }
    });

    setInputValue("");
    if (
      newIncluded.length !== included.length ||
      newExcluded.length !== excluded.length
    ) {
      onChange(newIncluded, newExcluded);
    }
  };

  const removeIncluded = (tagToRemove: string) => {
    onChange(
      included.filter((tag) => tag !== tagToRemove),
      excluded
    );
  };

  const removeExcluded = (tagToRemove: string) => {
    onChange(
      included,
      excluded.filter((tag) => tag !== tagToRemove)
    );
  };

  return (
    <div className={`relative flex items-center ${className}`}>
      <div
        className="flex-1 flex flex-wrap items-center gap-1.5 px-3 py-2 bg-secondary border border-border rounded-md text-foreground text-sm focus-within:outline-none focus-within:ring-2 focus-within:ring-primary min-h-[38px] cursor-text"
        onClick={() => inputRef.current?.focus()}
      >
        {included.map((tag) => (
          <span
            key={`inc-${tag}`}
            className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-muted text-foreground border border-border rounded-sm"
          >
            {tag}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                removeIncluded(tag);
              }}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        {excluded.map((tag) => (
          <span
            key={`exc-${tag}`}
            className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium border border-destructive bg-destructive/10 text-destructive rounded-sm"
          >
            !{tag}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                removeExcluded(tag);
              }}
              className="hover:opacity-80"
            >
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        <input
          id={id}
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => {
            if (inputValue.trim() !== "") {
              addTags(inputValue);
            }
          }}
          placeholder={
            included.length === 0 && excluded.length === 0 ? placeholder : ""
          }
          className="flex-1 min-w-[120px] bg-transparent border-none outline-none p-0 focus:ring-0"
        />
      </div>

      <Popover.Root>
        <Popover.Trigger asChild>
          <button
            type="button"
            className="absolute right-3 text-muted-foreground hover:text-foreground"
            aria-label="Symbol Filter Help"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            side="bottom"
            align="end"
            sideOffset={4}
            className="w-72 p-3 bg-popover text-popover-foreground rounded-md shadow-md border text-sm z-50"
          >
            <p className="font-semibold mb-2">Symbol Filter Guide</p>
            <ul className="list-disc pl-4 space-y-1 text-muted-foreground">
              <li>
                Type multiple symbols separated by commas (e.g.{" "}
                <code className="bg-muted px-1 rounded text-foreground">AAPL, MSFT</code>).
              </li>
              <li>
                Prefix with <code className="bg-muted px-1 rounded text-foreground">!</code> to exclude a symbol (e.g.{" "}
                <code className="bg-muted px-1 rounded text-foreground">!TSLA</code>).
              </li>
              <li>
                Matches are partial (e.g. <code className="bg-muted px-1 rounded text-foreground">APP</code> matches{" "}
                <code className="bg-muted px-1 rounded text-foreground">AAPL</code>).
              </li>
            </ul>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </div>
  );
}
