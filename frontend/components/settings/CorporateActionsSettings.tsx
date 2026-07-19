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
 * CorporateActionsSettings — manage stock splits and reverse splits.
 *
 * Allows users to define corporate actions (splits) that are applied during
 * broker import to adjust trade quantities and prices. The ratio is entered
 * as human-readable "Before → After" values and computed as `after / before`.
 *
 * Example: 1:20 reverse split → Before=20, After=1 → ratio = "0.05"
 * Example: 2:1 forward split  → Before=1,  After=2 → ratio = "2.0"
 */

"use client";

import { useState } from "react";
import {
  useListCorporateActions,
  useCreateCorporateAction,
  useUpdateCorporateAction,
  useDeleteCorporateAction,
} from "@/hooks/useCorporateActions";
import type { CorporateAction, CorporateActionCreate, CorporateActionUpdate } from "@/lib/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Convert a decimal ratio string to human-readable "X:Y" format. */
function ratioToDisplay(ratio: string): string {
  const r = parseFloat(ratio);
  if (isNaN(r) || r <= 0) return ratio;
  if (r >= 1) {
    // Forward split — show as "after:before", e.g. ratio=2 → "2:1"
    return `${r % 1 === 0 ? r.toFixed(0) : r}:1`;
  } else {
    // Reverse split — show as "1:before", e.g. ratio=0.05 → "1:20"
    const before = Math.round(1 / r);
    return `1:${before}`;
  }
}

// ─── Form state ───────────────────────────────────────────────────────────────

interface FormState {
  symbol: string;
  date: string;
  ratioBefore: string;
  ratioAfter: string;
  old_conid: string;
  new_conid: string;
}

const EMPTY_FORM: FormState = {
  symbol: "",
  date: "",
  ratioBefore: "",
  ratioAfter: "",
  old_conid: "",
  new_conid: "",
};

function formToPayload(form: FormState): CorporateActionCreate {
  const before = parseFloat(form.ratioBefore);
  const after = parseFloat(form.ratioAfter);
  const ratio = (after / before).toString();
  return {
    symbol: form.symbol.trim().toUpperCase(),
    date: form.date,
    ratio,
    old_conid: form.old_conid.trim() || null,
    new_conid: form.new_conid.trim() || null,
  };
}

function caToForm(ca: CorporateAction): FormState {
  const r = parseFloat(ca.ratio);
  // Reconstruct Before/After from ratio for the edit form
  // We normalise to integer-friendly fractions where possible
  let before: string;
  let after: string;
  if (r >= 1) {
    before = "1";
    after = r % 1 === 0 ? r.toFixed(0) : r.toString();
  } else {
    before = Math.round(1 / r).toString();
    after = "1";
  }
  return {
    symbol: ca.symbol,
    date: ca.date,
    ratioBefore: before,
    ratioAfter: after,
    old_conid: ca.old_conid ?? "",
    new_conid: ca.new_conid ?? "",
  };
}

// ─── Modal ────────────────────────────────────────────────────────────────────

interface ModalProps {
  title: string;
  form: FormState;
  onChange: (patch: Partial<FormState>) => void;
  onSubmit: () => void;
  onClose: () => void;
  isSubmitting: boolean;
  submitError: string | null;
  submitLabel: string;
}

function CorporateActionModal({
  title,
  form,
  onChange,
  onSubmit,
  onClose,
  isSubmitting,
  submitError,
  submitLabel,
}: ModalProps) {
  const before = parseFloat(form.ratioBefore);
  const after = parseFloat(form.ratioAfter);
  const previewRatio =
    !isNaN(before) && !isNaN(after) && before > 0 && after > 0
      ? (after / before).toFixed(6).replace(/\.?0+$/, "")
      : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-card rounded-xl border border-border shadow-xl p-6 w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-foreground">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          {/* Symbol */}
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              Symbol <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.symbol}
              onChange={(e) => onChange({ symbol: e.target.value })}
              placeholder="e.g. OTLK"
              className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Date */}
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              Split Date <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => onChange({ date: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Ratio */}
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              Split Ratio <span className="text-red-500">*</span>
            </label>
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <label className="block text-xs text-muted-foreground mb-1">Before</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={form.ratioBefore}
                  onChange={(e) => onChange({ ratioBefore: e.target.value })}
                  placeholder="e.g. 20"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex items-end pb-2">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 text-zinc-400 mt-5">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </div>
              <div className="flex-1">
                <label className="block text-xs text-muted-foreground mb-1">After</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={form.ratioAfter}
                  onChange={(e) => onChange({ ratioAfter: e.target.value })}
                  placeholder="e.g. 1"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
            {previewRatio !== null && (
              <p className="text-xs text-muted-foreground mt-1.5">
                Computed ratio: <span className="font-mono font-medium text-muted-foreground">{previewRatio}</span>
                {" "}({parseFloat(previewRatio) < 1 ? "reverse split" : "forward split"})
              </p>
            )}
          </div>

          {/* Old Conid */}
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              Old Conid <span className="text-zinc-400 font-normal">(optional — IBKR)</span>
            </label>
            <input
              type="text"
              value={form.old_conid}
              onChange={(e) => onChange({ old_conid: e.target.value })}
              placeholder="e.g. 357194941"
              className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* New Conid */}
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              New Conid <span className="text-zinc-400 font-normal">(optional — IBKR)</span>
            </label>
            <input
              type="text"
              value={form.new_conid}
              onChange={(e) => onChange({ new_conid: e.target.value })}
              placeholder="e.g. 690184975"
              className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        {submitError && (
          <p className="mt-3 text-sm text-red-500">{submitError}</p>
        )}

        <div className="flex justify-end gap-3 mt-6">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onSubmit}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-primary hover:bg-primary/90 disabled:opacity-50 text-white transition-colors"
          >
            {isSubmitting ? "Saving..." : submitLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Delete confirmation dialog ────────────────────────────────────────────────

interface DeleteDialogProps {
  ca: CorporateAction;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}

function DeleteConfirmDialog({ ca, onConfirm, onCancel, isDeleting }: DeleteDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-card rounded-xl border border-border shadow-xl p-6 w-full max-w-sm mx-4">
        <h2 className="text-base font-semibold text-foreground mb-2">Delete Corporate Action</h2>
        <p className="text-sm text-muted-foreground mb-5">
          Are you sure you want to delete the{" "}
          <span className="font-medium text-foreground">{ratioToDisplay(ca.ratio)}</span>{" "}
          split for <span className="font-medium text-foreground">{ca.symbol}</span>{" "}
          on {ca.date}? This cannot be undone.
        </p>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white transition-colors"
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function CorporateActionsSettings() {
  const { data: corporateActions, isLoading, isError } = useListCorporateActions();
  const createMutation = useCreateCorporateAction();
  const updateMutation = useUpdateCorporateAction();
  const deleteMutation = useDeleteCorporateAction();

  // Add modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [addForm, setAddForm] = useState<FormState>(EMPTY_FORM);
  const [addError, setAddError] = useState<string | null>(null);

  // Edit modal state
  const [editingCa, setEditingCa] = useState<CorporateAction | null>(null);
  const [editForm, setEditForm] = useState<FormState>(EMPTY_FORM);
  const [editError, setEditError] = useState<string | null>(null);

  // Delete dialog state
  const [deletingCa, setDeletingCa] = useState<CorporateAction | null>(null);

  // ── Add ──

  function openAddModal() {
    setAddForm(EMPTY_FORM);
    setAddError(null);
    setShowAddModal(true);
  }

  function handleAdd() {
    const { ratioBefore, ratioAfter, symbol, date } = addForm;
    if (!symbol.trim()) { setAddError("Symbol is required."); return; }
    if (!date) { setAddError("Date is required."); return; }
    const before = parseFloat(ratioBefore);
    const after = parseFloat(ratioAfter);
    if (isNaN(before) || isNaN(after) || before <= 0 || after <= 0) {
      setAddError("Before and After values must be positive numbers.");
      return;
    }
    setAddError(null);
    createMutation.mutate(formToPayload(addForm), {
      onSuccess: () => {
        setShowAddModal(false);
        setAddForm(EMPTY_FORM);
      },
      onError: (err) => {
        setAddError(err.message ?? "Failed to create corporate action.");
      },
    });
  }

  // ── Edit ──

  function openEditModal(ca: CorporateAction) {
    setEditingCa(ca);
    setEditForm(caToForm(ca));
    setEditError(null);
  }

  function handleEdit() {
    if (!editingCa) return;
    const { ratioBefore, ratioAfter, symbol, date } = editForm;
    if (!symbol.trim()) { setEditError("Symbol is required."); return; }
    if (!date) { setEditError("Date is required."); return; }
    const before = parseFloat(ratioBefore);
    const after = parseFloat(ratioAfter);
    if (isNaN(before) || isNaN(after) || before <= 0 || after <= 0) {
      setEditError("Before and After values must be positive numbers.");
      return;
    }
    setEditError(null);
    const payload: CorporateActionUpdate = formToPayload(editForm);
    updateMutation.mutate(
      { id: editingCa.id, payload },
      {
        onSuccess: () => {
          setEditingCa(null);
        },
        onError: (err) => {
          setEditError(err.message ?? "Failed to update corporate action.");
        },
      }
    );
  }

  // ── Delete ──

  function handleDelete() {
    if (!deletingCa) return;
    deleteMutation.mutate(deletingCa.id, {
      onSuccess: () => setDeletingCa(null),
    });
  }

  // ── Render ──

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-base font-semibold text-foreground">Corporate Actions</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Define stock splits and reverse splits. These are applied during import to adjust
            trade quantities and prices for positions that spanned a split event.
          </p>
        </div>
        <button
          type="button"
          onClick={openAddModal}
          className="shrink-0 ml-4 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-primary hover:bg-primary/90 text-white transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Add Split
        </button>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="py-10 text-center text-sm text-muted-foreground">Loading...</div>
      ) : isError ? (
        <div className="py-10 text-center text-sm text-red-500">Failed to load corporate actions.</div>
      ) : !corporateActions || corporateActions.length === 0 ? (
        <div className="py-10 text-center rounded-xl border border-dashed border-border text-muted-foreground text-sm">
          No corporate actions defined yet.{" "}
          <button
            type="button"
            onClick={openAddModal}
            className="text-primary hover:underline"
          >
            Add your first split.
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border">
                <th className="px-4 py-3 text-left">Symbol</th>
                <th className="px-4 py-3 text-left">Date</th>
                <th className="px-4 py-3 text-left">Ratio</th>
                <th className="px-4 py-3 text-left">Old Conid</th>
                <th className="px-4 py-3 text-left">New Conid</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[color-mix(in_srgb,var(--border)_50%,transparent)]">
              {corporateActions.map((ca) => (
                <tr key={ca.id} className="bg-card hover:bg-muted/50 transition-colors">
                  <td className="px-4 py-3 font-medium text-foreground">{ca.symbol}</td>
                  <td className="px-4 py-3 text-muted-foreground">{ca.date}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[color-mix(in_srgb,var(--warning)_10%,transparent)] text-warning border border-[color-mix(in_srgb,var(--warning)_20%,transparent)]">
                      {ratioToDisplay(ca.ratio)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                    {ca.old_conid ?? <span className="text-muted-foreground">—</span>}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                    {ca.new_conid ?? <span className="text-muted-foreground">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => openEditModal(ca)}
                        className="text-xs font-medium text-primary hover:underline"
                      >
                        Edit
                      </button>
                      <span className="text-muted-foreground">·</span>
                      <button
                        type="button"
                        onClick={() => setDeletingCa(ca)}
                        className="text-xs font-medium text-danger hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <CorporateActionModal
          title="Add Corporate Action"
          form={addForm}
          onChange={(patch) => setAddForm((prev) => ({ ...prev, ...patch }))}
          onSubmit={handleAdd}
          onClose={() => setShowAddModal(false)}
          isSubmitting={createMutation.isPending}
          submitError={addError}
          submitLabel="Add"
        />
      )}

      {/* Edit Modal */}
      {editingCa !== null && (
        <CorporateActionModal
          title="Edit Corporate Action"
          form={editForm}
          onChange={(patch) => setEditForm((prev) => ({ ...prev, ...patch }))}
          onSubmit={handleEdit}
          onClose={() => setEditingCa(null)}
          isSubmitting={updateMutation.isPending}
          submitError={editError}
          submitLabel="Save"
        />
      )}

      {/* Delete Dialog */}
      {deletingCa !== null && (
        <DeleteConfirmDialog
          ca={deletingCa}
          onConfirm={handleDelete}
          onCancel={() => setDeletingCa(null)}
          isDeleting={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
