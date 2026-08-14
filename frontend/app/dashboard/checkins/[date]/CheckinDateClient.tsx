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

import { useCheckinEntry, useCreateCheckin, useUpdateCheckin, useDeleteCheckin } from "@/hooks/useCheckins";
import { CheckinForm } from "@/components/checkin/CheckinForm";
import type { DailyCheckinCreate, DailyCheckinUpdate } from "@/lib/api/types.gen";
import { Loader2, AlertCircle, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import { toast } from "react-hot-toast";
interface Props {
  date: string;
}

export function CheckinDateClient({ date }: Props) {
  const router = useRouter();
  const { data: entry, isLoading: isEntryLoading } = useCheckinEntry(date);

  const createMutation = useCreateCheckin();
  const updateMutation = useUpdateCheckin();
  const deleteMutation = useDeleteCheckin();

  const handleSave = (data: DailyCheckinCreate | DailyCheckinUpdate) => {
    if (!entry) {
      createMutation.mutate(data as DailyCheckinCreate, {
        onSuccess: () => toast.success("Check-in saved successfully"),
      });
    } else {
      updateMutation.mutate(
        { date, payload: data as DailyCheckinUpdate },
        {
          onSuccess: () => toast.success("Check-in updated successfully"),
        }
      );
    }
  };

  const handleDelete = () => {
    if (confirm("Delete this check-in? This cannot be undone.")) {
      deleteMutation.mutate(date, {
        onSuccess: () => router.push("/dashboard/checkins"),
      });
    }
  };

  const isLoading = isEntryLoading;

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <Link
          href="/dashboard/checkins"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Timeline
        </Link>
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold">
              {format(new Date(`${date}T12:00:00Z`), "MMMM d, yyyy")}
            </h1>
            {entry && (
              <p className="text-sm text-muted-foreground mt-1">
                Updated {new Date(entry.updated_at).toLocaleString()}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="solid-card p-6 shadow-sm">
        {isLoading && !entry ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-6 h-6 text-muted-foreground animate-spin" />
          </div>
        ) : (
          <CheckinForm
            key={date}
            date={date}
            entry={entry}
            onSave={handleSave}
            onDelete={handleDelete}
            isSaving={createMutation.isPending || updateMutation.isPending}
            isDeleting={deleteMutation.isPending}
          />
        )}

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
    </div>
  );
}
