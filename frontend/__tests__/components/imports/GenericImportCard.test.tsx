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
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GenericImportCard } from "@/components/imports/GenericImportCard";
import {
  genericCsvTemplateApiV1ImportsFormatsGenericTemplateCsvGet,
  previewImportApiV1PortfoliosPortfolioIdImportsPreviewPost,
  uploadImportApiV1PortfoliosPortfolioIdImportsUploadPost,
} from "@/lib/api";
import type { ImportPreviewResult } from "@/lib/api/types.gen";

jest.mock("@/lib/api", () => ({
  previewImportApiV1PortfoliosPortfolioIdImportsPreviewPost: jest.fn(),
  uploadImportApiV1PortfoliosPortfolioIdImportsUploadPost: jest.fn(),
  genericCsvTemplateApiV1ImportsFormatsGenericTemplateCsvGet: jest.fn(),
}));

const mockPreview = jest.mocked(previewImportApiV1PortfoliosPortfolioIdImportsPreviewPost);
const mockUpload = jest.mocked(uploadImportApiV1PortfoliosPortfolioIdImportsUploadPost);
const mockTemplate = jest.mocked(genericCsvTemplateApiV1ImportsFormatsGenericTemplateCsvGet);

function previewResult(overrides: Partial<ImportPreviewResult> = {}): ImportPreviewResult {
  return {
    detected_strategy: "external_id",
    recorded_strategy: null,
    strategy_conflict: false,
    total: 3,
    new: 2,
    already_imported: 1,
    suppressed: 0,
    new_splits: 1,
    conflicting_splits: 0,
    warnings: [],
    errors: [],
    ...overrides,
  };
}

// The SDK functions return a RequestResult; the hooks only read data/error.
function sdkResult(data: unknown, error: unknown = undefined) {
  return { data, error } as never;
}

function renderCard() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <GenericImportCard portfolioId="portfolio-1" accountId="account-1" />
    </QueryClientProvider>,
  );
}

function selectFile(name = "executions.json") {
  const file = new File(["{}"], name, { type: "application/json" });
  fireEvent.change(screen.getByLabelText("Execution file"), { target: { files: [file] } });
  return file;
}

describe("GenericImportCard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("accepts only JSON and CSV and links format help", () => {
    renderCard();
    expect(screen.getByLabelText("Execution file")).toHaveAttribute("accept", ".json,.csv");
    expect(screen.getByRole("link", { name: "Format help" })).toHaveAttribute("href", "/help#import-from-other-brokers");
    expect(screen.queryByRole("button", { name: "Confirm import" })).not.toBeInTheDocument();
  });

  it("previews the selected file and imports only after explicit confirmation", async () => {
    mockPreview.mockResolvedValue(sdkResult({ data: previewResult() }));
    mockUpload.mockResolvedValue(
      sdkResult({ data: { broker: "generic", filename: "executions.json", trades_parsed: 1, trades_created: 1, trades_skipped: 0, raw_transactions_created: 2, warnings: [] } }),
    );
    renderCard();
    const file = selectFile();

    expect(await screen.findByLabelText("Import preview")).toBeInTheDocument();
    expect(mockPreview).toHaveBeenCalledWith({ path: { portfolio_id: "portfolio-1" }, body: { account_id: "account-1", file } });
    expect(screen.getByText("Executions in file").nextSibling).toHaveTextContent("3");
    expect(screen.getByText("New").nextSibling).toHaveTextContent("2");
    expect(screen.getByText("Already imported").nextSibling).toHaveTextContent("1");
    expect(screen.getByText("Broker fill IDs (external_id)")).toBeInTheDocument();
    expect(screen.getByText(/Not set yet/)).toBeInTheDocument();
    expect(mockUpload).not.toHaveBeenCalled();

    const confirm = screen.getByRole("button", { name: "Confirm import" });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);

    expect(await screen.findByRole("status")).toHaveTextContent("Imported 2 new executions; 1 trade created.");
    expect(mockUpload).toHaveBeenCalledWith({ path: { portfolio_id: "portfolio-1" }, body: { account_id: "account-1", file } });
  });

  it("disables confirmation and explains how to resolve a strategy conflict", async () => {
    mockPreview.mockResolvedValue(
      sdkResult({ data: previewResult({ detected_strategy: "external_id", recorded_strategy: "fingerprint", strategy_conflict: true }) }),
    );
    renderCard();
    selectFile();

    expect(await screen.findByText(/different ID strategy/)).toHaveTextContent("clear all trades of this account");
    expect(screen.getByRole("button", { name: "Confirm import" })).toBeDisabled();
  });

  it("shows row-level validation errors and keeps confirmation disabled", async () => {
    mockPreview.mockResolvedValue(
      sdkResult(undefined, {
        detail: [
          { row: 0, field: "executed_at", code: "timezone_aware", message: "Invalid field value" },
          { row: null, field: "external_id", code: "mixed_id_strategy", message: "Supply external_id on every execution or none" },
        ],
      }),
    );
    renderCard();
    selectFile();

    expect(await screen.findByText(/The file was rejected/)).toBeInTheDocument();
    expect(screen.getByText("Row 0 · executed_at · timezone_aware: Invalid field value")).toBeInTheDocument();
    expect(screen.getByText(/File · external_id · mixed_id_strategy/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm import" })).toBeDisabled();
    expect(mockUpload).not.toHaveBeenCalled();
  });

  it("shows split conflicts and warnings from the preview", async () => {
    mockPreview.mockResolvedValue(
      sdkResult({ data: previewResult({ conflicting_splits: 1, warnings: ["split_conflict: existing split ratio preserved"] }) }),
    );
    renderCard();
    selectFile();

    expect(await screen.findByText(/split_conflict: existing split ratio preserved/)).toBeInTheDocument();
    expect(screen.getByText("Conflicting splits").nextSibling).toHaveTextContent("1");
    expect(screen.getByRole("button", { name: "Confirm import" })).toBeEnabled();
  });

  it("re-runs the preview when another file is selected", async () => {
    mockPreview.mockResolvedValueOnce(sdkResult({ data: previewResult({ total: 3 }) }));
    mockPreview.mockResolvedValueOnce(sdkResult({ data: previewResult({ total: 7 }) }));
    renderCard();
    selectFile("first.json");
    await waitFor(() => expect(screen.getByText("Executions in file").nextSibling).toHaveTextContent("3"));
    selectFile("second.csv");
    await waitFor(() => expect(screen.getByText("Executions in file").nextSibling).toHaveTextContent("7"));
    expect(mockPreview).toHaveBeenCalledTimes(2);
  });

  it("downloads the CSV template through the authenticated SDK client", async () => {
    const createObjectURL = jest.fn().mockReturnValue("blob:template");
    const revokeObjectURL = jest.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    mockTemplate.mockResolvedValue(sdkResult(new Blob(["executed_at\n"], { type: "text/csv" })));
    renderCard();

    fireEvent.click(screen.getByRole("button", { name: "Download CSV template" }));

    await waitFor(() => expect(click).toHaveBeenCalled());
    expect(mockTemplate).toHaveBeenCalledWith({ parseAs: "blob" });
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:template");
    click.mockRestore();
  });
});
