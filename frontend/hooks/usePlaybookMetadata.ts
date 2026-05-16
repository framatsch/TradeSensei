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
 * React Query hooks for playbook taxonomy assignments, attachments, and links.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  assignPlaybookTaxonomyApiV1PlaybooksPlaybookIdTaxonomiesPost,
  removePlaybookTaxonomyApiV1PlaybooksPlaybookIdTaxonomiesTaxonomyIdDelete,
  listPlaybookTaxonomiesApiV1PlaybooksPlaybookIdTaxonomiesGet,
  generateUploadUrlApiV1PlaybooksPlaybookIdAttachmentsUploadUrlPost,
  registerAttachmentApiV1PlaybooksPlaybookIdAttachmentsPost,
  listAttachmentsApiV1PlaybooksPlaybookIdAttachmentsGet,
  deleteAttachmentApiV1PlaybooksPlaybookIdAttachmentsAttachmentIdDelete,
  listLinksApiV1PlaybooksPlaybookIdLinksGet,
  createLinkApiV1PlaybooksPlaybookIdLinksPost,
  deleteLinkApiV1PlaybooksPlaybookIdLinksLinkIdDelete,
} from "@/lib/api/index";
import type {
  TaxonomyResponse,
  PlaybookImageResponse,
  PlaybookImageUploadUrlResponse,
  PlaybookLinkResponse,
} from "@/lib/api/types.gen";

// ─── Taxonomy assignments ────────────────────────────────────────────────────

export function usePlaybookTaxonomies(playbookId: string) {
  return useQuery<TaxonomyResponse[], Error>({
    queryKey: ["playbook", playbookId, "taxonomies"],
    queryFn: async () => {
      const { data, error } = await listPlaybookTaxonomiesApiV1PlaybooksPlaybookIdTaxonomiesGet({
        path: { playbook_id: playbookId },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data as TaxonomyResponse[];
    },
    enabled: !!playbookId,
  });
}

export function useAssignPlaybookTaxonomy() {
  const qc = useQueryClient();
  return useMutation<void, Error, { playbookId: string; taxonomyId: string }>({
    mutationFn: async ({ playbookId, taxonomyId }) => {
      const { error } = await assignPlaybookTaxonomyApiV1PlaybooksPlaybookIdTaxonomiesPost({
        path: { playbook_id: playbookId },
        body: { taxonomy_id: taxonomyId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["playbook", variables.playbookId, "taxonomies"] });
    },
  });
}

export function useRemovePlaybookTaxonomy() {
  const qc = useQueryClient();
  return useMutation<void, Error, { playbookId: string; taxonomyId: string }>({
    mutationFn: async ({ playbookId, taxonomyId }) => {
      const { error } = await removePlaybookTaxonomyApiV1PlaybooksPlaybookIdTaxonomiesTaxonomyIdDelete({
        path: { playbook_id: playbookId, taxonomy_id: taxonomyId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["playbook", variables.playbookId, "taxonomies"] });
    },
  });
}

// ─── Attachments ─────────────────────────────────────────────────────────────

export function usePlaybookAttachments(playbookId: string) {
  return useQuery<PlaybookImageResponse[], Error>({
    queryKey: ["playbook", playbookId, "attachments"],
    queryFn: async () => {
      const { data, error } = await listAttachmentsApiV1PlaybooksPlaybookIdAttachmentsGet({
        path: { playbook_id: playbookId },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data as PlaybookImageResponse[];
    },
    enabled: !!playbookId,
  });
}

export function usePlaybookImageUploadUrl() {
  return useMutation<
    PlaybookImageUploadUrlResponse,
    Error,
    { playbookId: string; filename: string; contentType: string }
  >({
    mutationFn: async ({ playbookId, filename, contentType }) => {
      const { data, error } = await generateUploadUrlApiV1PlaybooksPlaybookIdAttachmentsUploadUrlPost({
        path: { playbook_id: playbookId },
        body: { filename, content_type: contentType },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data as PlaybookImageUploadUrlResponse;
    },
  });
}

export function useRegisterPlaybookAttachment() {
  const qc = useQueryClient();
  return useMutation<
    PlaybookImageResponse,
    Error,
    { playbookId: string; filename: string; contentType: string; storageUrl: string }
  >({
    mutationFn: async ({ playbookId, filename, contentType, storageUrl }) => {
      const { data, error } = await registerAttachmentApiV1PlaybooksPlaybookIdAttachmentsPost({
        path: { playbook_id: playbookId },
        body: { filename, content_type: contentType, storage_url: storageUrl },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data as PlaybookImageResponse;
    },
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["playbook", variables.playbookId, "attachments"] });
    },
  });
}

export function useDeletePlaybookAttachment() {
  const qc = useQueryClient();
  return useMutation<void, Error, { playbookId: string; attachmentId: string }>({
    mutationFn: async ({ playbookId, attachmentId }) => {
      const { error } = await deleteAttachmentApiV1PlaybooksPlaybookIdAttachmentsAttachmentIdDelete({
        path: { playbook_id: playbookId, attachment_id: attachmentId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["playbook", variables.playbookId, "attachments"] });
    },
  });
}

// ─── Links ────────────────────────────────────────────────────────────────────

export function usePlaybookLinks(playbookId: string) {
  return useQuery<PlaybookLinkResponse[], Error>({
    queryKey: ["playbook", playbookId, "links"],
    queryFn: async () => {
      const { data, error } = await listLinksApiV1PlaybooksPlaybookIdLinksGet({
        path: { playbook_id: playbookId },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data as PlaybookLinkResponse[];
    },
    enabled: !!playbookId,
  });
}

export function useCreatePlaybookLink() {
  const qc = useQueryClient();
  return useMutation<PlaybookLinkResponse, Error, { playbookId: string; label: string; url: string }>({
    mutationFn: async ({ playbookId, label, url }) => {
      const { data, error } = await createLinkApiV1PlaybooksPlaybookIdLinksPost({
        path: { playbook_id: playbookId },
        body: { label, url },
      });
      if (error || !data) throw error ?? new Error("Request failed: no data returned");
      return data as PlaybookLinkResponse;
    },
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["playbook", variables.playbookId, "links"] });
    },
  });
}

export function useDeletePlaybookLink() {
  const qc = useQueryClient();
  return useMutation<void, Error, { playbookId: string; linkId: string }>({
    mutationFn: async ({ playbookId, linkId }) => {
      const { error } = await deleteLinkApiV1PlaybooksPlaybookIdLinksLinkIdDelete({
        path: { playbook_id: playbookId, link_id: linkId },
      });
      if (error) throw error ?? new Error("Request failed");
    },
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: ["playbook", variables.playbookId, "links"] });
    },
  });
}
