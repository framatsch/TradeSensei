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
import userEvent from "@testing-library/user-event";
import { PlaybookEditorClient } from "@/components/playbooks/PlaybookEditorClient";

const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockUpdatePlaybook = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useSearchParams: () => ({
    get: (key: string) => (key === "edit" ? "true" : null),
  }),
}));

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock("remark-gfm", () => ({
  __esModule: true,
  default: jest.fn(),
}));

jest.mock("rehype-sanitize", () => ({
  __esModule: true,
  default: jest.fn(),
}));

jest.mock("react-hot-toast", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock("@/hooks/usePlaybooks", () => ({
  usePlaybooks: () => ({
    data: [
      {
        id: "playbook-1",
        user_id: "user-1",
        name: "Breakout",
        description: "Description from API",
        content_markdown: "Legacy markdown",
        target_winrate: "0.60",
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        taxonomies: [],
      },
    ],
    isLoading: false,
  }),
  useUpdatePlaybook: () => ({
    mutate: mockUpdatePlaybook,
    isPending: false,
  }),
  useDeletePlaybook: () => ({
    mutateAsync: jest.fn(),
    isPending: false,
  }),
}));

jest.mock("@/hooks/useTaxonomies", () => ({
  useGetTaxonomies: () => ({ data: [] }),
}));

jest.mock("@/hooks/usePlaybookMetadata", () => ({
  usePlaybookTaxonomies: () => ({ data: [], isSuccess: true }),
  useAssignPlaybookTaxonomy: () => ({ mutate: jest.fn() }),
  useRemovePlaybookTaxonomy: () => ({ mutate: jest.fn() }),
  usePlaybookAttachments: () => ({ data: [], isSuccess: true }),
  usePlaybookImageUploadUrl: () => ({ mutateAsync: jest.fn() }),
  useRegisterPlaybookAttachment: () => ({ mutateAsync: jest.fn() }),
  useDeletePlaybookAttachment: () => ({ mutateAsync: jest.fn() }),
  usePlaybookLinks: () => ({ data: [], isSuccess: true }),
  useCreatePlaybookLink: () => ({ mutate: jest.fn(), isPending: false }),
  useDeletePlaybookLink: () => ({ mutate: jest.fn() }),
}));

describe("PlaybookEditorClient", () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockReplace.mockReset();
    mockUpdatePlaybook.mockReset();
  });

  it("binds editor content to description and saves description in payload", async () => {
    const user = userEvent.setup();

    render(<PlaybookEditorClient id="playbook-1" />);

    const editor = screen.getByLabelText("Playbook content (Markdown)");
    expect(editor).toHaveValue("Description from API");

    await user.clear(editor);
    await user.type(editor, "Updated description body");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(mockUpdatePlaybook).toHaveBeenCalledWith(
      {
        id: "playbook-1",
        payload: expect.objectContaining({
          name: "Breakout",
          description: "Updated description body",
          target_winrate: 0.6,
        }),
      },
      expect.any(Object)
    );

    const mutationArg = mockUpdatePlaybook.mock.calls[0]?.[0] as
      | { payload?: Record<string, unknown> }
      | undefined;
    expect(mutationArg?.payload).not.toHaveProperty("content_markdown");
    expect(mutationArg?.payload).toHaveProperty("is_active", true);
  });

  it("toggles active status and saves updated is_active flag", async () => {
    const user = userEvent.setup();

    render(<PlaybookEditorClient id="playbook-1" />);

    const statusToggle = screen.getByRole("button", {
      name: "Toggle active status, currently Active",
    });
    expect(statusToggle).toBeInTheDocument();

    await user.click(statusToggle);
    expect(
      screen.getByRole("button", { name: "Toggle active status, currently Inactive" })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(mockUpdatePlaybook).toHaveBeenCalledWith(
      {
        id: "playbook-1",
        payload: expect.objectContaining({
          is_active: false,
        }),
      },
      expect.any(Object)
    );
  });

  it("stays in edit mode on Save and exits edit mode on Save & Close", async () => {
    const user = userEvent.setup();
    mockUpdatePlaybook.mockImplementation((_vars, options) => {
      options?.onSuccess?.();
    });

    render(<PlaybookEditorClient id="playbook-1" />);

    // Clicking "Save" keeps edit mode active and URL with ?edit=true
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(mockReplace).toHaveBeenCalledWith("/dashboard/library/playbooks/playbook-1?edit=true");
    expect(screen.getByLabelText("Playbook content (Markdown)")).toBeInTheDocument();

    // Clicking "Save & Close" exits edit mode and strips ?edit=true
    await user.click(screen.getByRole("button", { name: "Save & Close" }));
    expect(mockReplace).toHaveBeenCalledWith("/dashboard/library/playbooks/playbook-1");
    expect(screen.queryByLabelText("Playbook content (Markdown)")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
  });

  it("renders mobile pane switcher tabs (Document and Details & Media)", async () => {
    const user = userEvent.setup();

    render(<PlaybookEditorClient id="playbook-1" />);

    const docTab = screen.getByRole("tab", { name: /Document/i });
    const detailsTab = screen.getByRole("tab", { name: /Details & Media/i });

    expect(docTab).toHaveAttribute("aria-selected", "true");
    expect(detailsTab).toHaveAttribute("aria-selected", "false");

    await user.click(detailsTab);
    expect(docTab).toHaveAttribute("aria-selected", "false");
    expect(detailsTab).toHaveAttribute("aria-selected", "true");
  });
});
