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

import React from "react";
import { render, screen } from "@testing-library/react";
import { QualitativeMetadataPanel } from "@/components/trades/QualitativeMetadataPanel";
import useFeatureFlag from "@/hooks/useFeatureFlag";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { useGetAnnotationDefinitions } from "@/hooks/useAnnotationDefinitions";
import {
  useAssignTradeTaxonomy,
  useRemoveTradeTaxonomy,
  useAssignTradeAnnotation,
  useUpdateTradeAnnotation,
} from "@/hooks/useTradeMetadata";
import { useUpdateTrade } from "@/hooks/useTrade";
import { useDeleteNote } from "@/hooks/useNotes";
import { usePlaybooks } from "@/hooks/usePlaybooks";

jest.mock("@/hooks/useFeatureFlag", () => ({
  __esModule: true,
  default: jest.fn(() => false),
}));
jest.mock("@/hooks/useTaxonomies", () => ({
  useGetTaxonomies: jest.fn(),
}));
jest.mock("@/hooks/useAnnotationDefinitions", () => ({
  useGetAnnotationDefinitions: jest.fn(),
}));
jest.mock("@/hooks/useTradeMetadata", () => ({
  useAssignTradeTaxonomy: jest.fn(),
  useRemoveTradeTaxonomy: jest.fn(),
  useAssignTradeAnnotation: jest.fn(),
  useUpdateTradeAnnotation: jest.fn(),
}));
jest.mock("@/hooks/useTrade", () => ({
  useUpdateTrade: jest.fn(),
}));
jest.mock("@/hooks/useNotes", () => ({
  useDeleteNote: jest.fn(),
}));
jest.mock("@/hooks/usePlaybooks", () => ({
  usePlaybooks: jest.fn(),
}));
// Mock MarkdownRenderer to avoid ESM issues from react-markdown (see NoteForm.test.tsx)
jest.mock("@/components/notes/MarkdownRenderer", () => ({
  MarkdownRenderer: ({ content }: { content: string }) => (
    <div data-testid="markdown-preview">{content}</div>
  ),
}));

const convictionDef: any = {
  id: "def-1",
  name: "Conviction",
  type: "int",
  scope: "trades",
  scale_labels: { min: 1, max: 5 },
  is_archived: false,
  created_at: "2024-01-01",
  updated_at: "2024-01-01",
  description: null,
  icon_identifier: null,
};

function buildTrade(overrides: Record<string, unknown> = {}): any {
  return {
    id: "trade-1",
    journal: null,
    playbook_id: null,
    taxonomies: [],
    trade_notes: [],
    annotations: [
      {
        trade_id: "trade-1",
        annotation_definition_id: "def-1",
        name: "Conviction",
        type: "int",
        scope: "trades",
        icon_identifier: null,
        value: 4,
      },
    ],
    ...overrides,
  };
}

describe("QualitativeMetadataPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useGetTaxonomies as jest.Mock).mockReturnValue({ data: [] });
    (useGetAnnotationDefinitions as jest.Mock).mockReturnValue({ data: [convictionDef] });
    (usePlaybooks as jest.Mock).mockReturnValue({ data: [] });
    (useUpdateTrade as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useDeleteNote as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useAssignTradeTaxonomy as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useRemoveTradeTaxonomy as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useAssignTradeAnnotation as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useUpdateTradeAnnotation as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
  });

  it("pre-fills annotation inputs from trade.annotations on initial render", () => {
    render(<QualitativeMetadataPanel trade={buildTrade()} />);

    // Regression test: previously draftAnnotations was always initialized to {}
    // regardless of trade.annotations, so persisted values (including ones written
    // out-of-band via the MCP server) never appeared in the form after a page load.
    expect(screen.getByDisplayValue("4")).toBeInTheDocument();
  });

  it("does not show an 'Unsaved changes' indicator for values already persisted on the trade", () => {
    render(<QualitativeMetadataPanel trade={buildTrade()} />);

    expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument();
  });

  it("re-seeds annotation inputs when switching to a different trade", () => {
    const { rerender } = render(<QualitativeMetadataPanel trade={buildTrade()} />);
    expect(screen.getByDisplayValue("4")).toBeInTheDocument();

    const otherTrade = buildTrade({
      id: "trade-2",
      annotations: [
        {
          trade_id: "trade-2",
          annotation_definition_id: "def-1",
          name: "Conviction",
          type: "int",
          scope: "trades",
          icon_identifier: null,
          value: 2,
        },
      ],
    });
    rerender(<QualitativeMetadataPanel trade={otherTrade} />);

    expect(screen.getByDisplayValue("2")).toBeInTheDocument();
  });

  it("filters out inactive playbooks for unassigned trades", () => {
    (usePlaybooks as jest.Mock).mockReturnValue({
      data: [
        { id: "pb-1", name: "Active Strategy", is_active: true },
        { id: "pb-2", name: "Retired Strategy", is_active: false },
      ],
    });

    render(<QualitativeMetadataPanel trade={buildTrade({ playbook_id: null })} />);

    expect(screen.getByRole("option", { name: "Active Strategy" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /retired strategy/i })).not.toBeInTheDocument();
  });

  it("preserves and labels assigned inactive playbook", () => {
    (usePlaybooks as jest.Mock).mockReturnValue({
      data: [
        { id: "pb-1", name: "Active Strategy", is_active: true },
        { id: "pb-2", name: "Retired Strategy", is_active: false },
      ],
    });

    render(<QualitativeMetadataPanel trade={buildTrade({ playbook_id: "pb-2" })} />);

    expect(screen.getByRole("option", { name: "Active Strategy" })).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Retired Strategy (Inactive)" })
    ).toBeInTheDocument();
  });
});
