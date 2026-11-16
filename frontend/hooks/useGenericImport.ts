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
 * React Query hooks for the generic (Trade Sensei Execution Format) import:
 * read-only preview, confirmed upload and the authenticated CSV template.
 */

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  genericCsvTemplateApiV1ImportsFormatsGenericTemplateCsvGet,
  previewImportApiV1PortfoliosPortfolioIdImportsPreviewPost,
  uploadImportApiV1PortfoliosPortfolioIdImportsUploadPost,
} from "@/lib/api";
import type { GenericValidationIssue, ImportPreviewResult, ImportResult } from "@/lib/api/types.gen";
import { extractApiError } from "@/lib/apiErrors";

export interface GenericImportRequest {
  portfolioId: string;
  accountId: string;
  file: File;
}

/** Error thrown by preview/upload: row-level issues when the file is invalid. */
export class GenericImportError extends Error {
  readonly issues: GenericValidationIssue[];

  constructor(message: string, issues: GenericValidationIssue[] = []) {
    super(message);
    this.name = "GenericImportError";
    this.issues = issues;
  }
}

function isIssue(value: unknown): value is GenericValidationIssue {
  return typeof value === "object" && value !== null && "code" in value && "field" in value && "message" in value;
}

/** Map an SDK error body to a GenericImportError, keeping row issues. */
function toImportError(error: unknown, fallback: string): GenericImportError {
  const detail = typeof error === "object" && error !== null ? (error as { detail?: unknown }).detail : undefined;
  if (Array.isArray(detail) && detail.every(isIssue)) {
    return new GenericImportError("The file failed validation.", detail);
  }
  return new GenericImportError(extractApiError(error, fallback));
}

export function useGenericImportPreview() {
  return useMutation<ImportPreviewResult, GenericImportError, GenericImportRequest>({
    mutationFn: async ({ portfolioId, accountId, file }) => {
      const { data, error } = await previewImportApiV1PortfoliosPortfolioIdImportsPreviewPost({
        path: { portfolio_id: portfolioId },
        body: { account_id: accountId, file },
      });
      if (error || !data) throw toImportError(error, "Preview failed.");
      return data.data;
    },
  });
}

export function useGenericImportUpload() {
  const qc = useQueryClient();
  return useMutation<ImportResult, GenericImportError, GenericImportRequest>({
    mutationFn: async ({ portfolioId, accountId, file }) => {
      const { data, error } = await uploadImportApiV1PortfoliosPortfolioIdImportsUploadPost({
        path: { portfolio_id: portfolioId },
        body: { account_id: accountId, file },
      });
      if (error || !data) throw toImportError(error, "Import failed.");
      return data.data;
    },
    onSuccess: () => {
      for (const key of ["trades", "metrics", "tax", "stats", "accounts"]) {
        void qc.invalidateQueries({ queryKey: [key] });
      }
    },
  });
}

export const GENERIC_TEMPLATE_FILENAME = "tradesensei-executions-v1.csv";

/** Download the CSV template through the authenticated SDK client. */
export function useGenericTemplateDownload() {
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      const { data, error } = await genericCsvTemplateApiV1ImportsFormatsGenericTemplateCsvGet({ parseAs: "blob" });
      if (error || !(data instanceof Blob)) throw new Error(extractApiError(error, "Template download failed."));
      const url = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = url;
      link.download = GENERIC_TEMPLATE_FILENAME;
      link.click();
      URL.revokeObjectURL(url);
    },
  });
}
