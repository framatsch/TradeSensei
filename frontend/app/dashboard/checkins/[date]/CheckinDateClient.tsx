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

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "react-hot-toast";
import { Loader2, AlertCircle } from "lucide-react";
import {
  useCheckinEntry,
  useCheckinEntries,
  useCreateCheckin,
  useUpdateCheckin,
  useDeleteCheckin,
} from "@/hooks/useCheckins";
import {
  useAssignCheckinTaxonomy,
  useAssignCheckinAnnotation,
} from "@/hooks/useCheckinMetadata";
import { CheckinForm, type CheckinSaveOptions } from "@/components/checkin/CheckinForm";
import type {
  DailyCheckinCreate,
  DailyCheckinUpdate,
  AnnotationAssignRequest,
} from "@/lib/api/types.gen";

interface Props {
  date: string;
}

export function CheckinDateClient({ date }: Props) {
  const router = useRouter();
  const { data: entry, isLoading: isEntryLoading } = useCheckinEntry(date);

  // Fetch existing entries to compute chronologically adjacent Prev / Next entry dates
  const { data: entriesData } = useCheckinEntries(
    undefined,
    undefined,
    undefined,
    undefined,
    undefined,
    200
  );

  const { prevEntryDate, nextEntryDate } = useMemo(() => {
    const items = entriesData?.items ?? [];
    const sortedDates = Array.from(new Set(items.map((item) => item.date))).sort();
    const prev = [...sortedDates].reverse().find((d) => d < date) ?? null;
    const next = sortedDates.find((d) => d > date) ?? null;
    return { prevEntryDate: prev, nextEntryDate: next };
  }, [entriesData, date]);

  const createMutation = useCreateCheckin();
  const updateMutation = useUpdateCheckin();
  const deleteMutation = useDeleteCheckin();
  const assignTaxonomyMutation = useAssignCheckinTaxonomy();
  const assignAnnotationMutation = useAssignCheckinAnnotation();
  const [isSyncingMetadata, setIsSyncingMetadata] = useState(false);

  const handleSave = async (
    data: DailyCheckinCreate | DailyCheckinUpdate,
    options?: CheckinSaveOptions
  ) => {
    if (!entry) {
      const created = await createMutation.mutateAsync(data as DailyCheckinCreate);

      // Flush buffered tags and annotations immediately after creating the new check-in
      const bufferedTagIds = options?.bufferedTagIds ?? [];
      const bufferedAnnotations = options?.bufferedAnnotations ?? {};
      const annotationEntries = Object.entries(bufferedAnnotations).filter(
        ([, val]) => val !== null && val !== undefined
      );

      if (bufferedTagIds.length > 0 || annotationEntries.length > 0) {
        setIsSyncingMetadata(true);
        try {
          for (const taxonomyId of bufferedTagIds) {
            await assignTaxonomyMutation.mutateAsync({
              checkinId: created.id,
              taxonomyId,
            });
          }
          for (const [annotationDefinitionId, value] of annotationEntries) {
            await assignAnnotationMutation.mutateAsync({
              checkinId: created.id,
              annotationDefinitionId,
              value: value as AnnotationAssignRequest["value"],
            });
          }
        } catch {
          toast.error("Check-in saved, but some tags or annotations failed to save.");
        } finally {
          setIsSyncingMetadata(false);
        }
      }

      toast.success("Check-in saved successfully");
    } else {
      await updateMutation.mutateAsync({
        date,
        payload: data as DailyCheckinUpdate,
      });
      toast.success("Check-in updated successfully");
    }
  };

  const handleDelete = () => {
    if (confirm("Delete this check-in? This cannot be undone.")) {
      deleteMutation.mutate(date, {
        onSuccess: () => router.push("/dashboard/checkins"),
      });
    }
  };

  if (isEntryLoading && !entry) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-6 h-6 text-muted-foreground animate-spin" />
      </div>
    );
  }

  return (
    <div className="w-full p-4 sm:p-6">
      <CheckinForm
        key={date}
        date={date}
        entry={entry}
        prevEntryDate={prevEntryDate}
        nextEntryDate={nextEntryDate}
        onSave={handleSave}
        onDelete={handleDelete}
        isSaving={
          createMutation.isPending ||
          updateMutation.isPending ||
          isSyncingMetadata
        }
        isDeleting={deleteMutation.isPending}
      />

      {createMutation.isError && (
        <div className="mt-4 flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">
          <AlertCircle className="w-4 h-4" />
          {createMutation.error?.message ?? "Failed to create check-in"}
        </div>
      )}
      {updateMutation.isError && (
        <div className="mt-4 flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">
          <AlertCircle className="w-4 h-4" />
          {updateMutation.error?.message ?? "Failed to update check-in"}
        </div>
      )}
    </div>
  );
}
