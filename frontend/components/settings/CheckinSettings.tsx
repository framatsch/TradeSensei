/**
 * CheckinSettings — manage MarketPhaseDefinition and CheckinFieldDefinition
 * entities from the global settings module.
 */

"use client";

import { useState } from "react";
import {
  useMarketIndexes,
  useCreateMarketIndex,
  useUpdateMarketIndex,
  useDeleteMarketIndex,
  useMarketPhases,
  useCreateMarketPhase,
  useUpdateMarketPhase,
  useCheckinFields,
  useCreateCheckinField,
  useUpdateCheckinField,
} from "@/hooks/useCheckinDefinitions";
import type {
  MarketIndexDefinitionResponse,
  MarketIndexDefinitionCreate,
  MarketIndexDefinitionUpdate,
  MarketPhaseDefinitionRead,
  MarketPhaseDefinitionCreate,
  MarketPhaseDefinitionUpdate,
  CheckinFieldDefinitionRead,
  CheckinFieldDefinitionCreate,
  CheckinFieldDefinitionUpdate,
  FieldTypeEnum,
} from "@/lib/api/types.gen";

// ─── Market Phase form state ──────────────────────────────────────────────────

interface PhaseFormState {
  name: string;
  label: string;
  color_hex: string;
}

const EMPTY_PHASE_FORM: PhaseFormState = {
  name: "",
  label: "",
  color_hex: "#6366f1",
};

function validatePhaseKey(name: string): string | null {
  if (!name.trim()) return "Key is required.";
  if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(name.trim().toLowerCase()))
    return "Key must be lowercase kebab-case (e.g. bullish, bearish, low-vol).";
  if (name.trim().length > 50) return "Key must be 50 characters or less.";
  return null;
}

function validatePhaseLabel(label: string): string | null {
  if (!label.trim()) return "Label is required.";
  if (label.trim().length > 100) return "Label must be 100 characters or less.";
  return null;
}

// ─── Check-in Field form state ────────────────────────────────────────────────

interface FieldFormState {
  field_name: string;
  field_type: FieldTypeEnum;
}

const EMPTY_FIELD_FORM: FieldFormState = {
  field_name: "",
  field_type: "integer",
};

function validateFieldKey(name: string): string | null {
  if (!name.trim()) return "Key is required.";
  if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(name.trim().toLowerCase()))
    return "Key must be lowercase kebab-case (e.g. mood-level, focus, rule-followed).";
  if (name.trim().length > 50) return "Key must be 50 characters or less.";
  return null;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function ColorPickerButton({ color, onChange }: { color: string; onChange: (c: string) => void }) {
  return (
    <span className="relative inline-flex items-center gap-2">
      <input
        type="color"
        value={color}
        onChange={(e) => onChange(e.target.value)}
        className="w-7 h-7 rounded-md border border-border cursor-pointer p-0 bg-transparent"
      />
      <span className="text-sm font-mono text-muted-foreground">{color}</span>
    </span>
  );
}

function FieldTypeBadge({ fieldType }: { fieldType: FieldTypeEnum }) {
  const colors: Record<FieldTypeEnum, string> = {
    integer: "bg-[color-mix(in_srgb,hsl(var(--primary))_10%,transparent)] text-primary border-[color-mix(in_srgb,hsl(var(--primary))_20%,transparent)]",
    boolean: "bg-[color-mix(in_srgb,hsl(var(--secondary))_10%,transparent)] text-secondary-foreground border-[color-mix(in_srgb,hsl(var(--secondary))_20%,transparent)]",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colors[fieldType]}`}>
      {fieldType === "integer" ? "Integer" : "Boolean"}
    </span>
  );
}

function StatusToggle({ enabled, onChange }: { enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={() => onChange(!enabled)}
      className={`relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
        enabled ? "bg-primary" : "bg-muted"
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-150 ${
          enabled ? "translate-x-6" : "translate-x-1"
        }`}
      />
    </button>
  );
}

// ─── Market Indexes Section ──────────────────────────────────────────────────

function MarketIndexesSection() {
  const { data: indexes, isLoading, isError } = useMarketIndexes();
  const createMutation = useCreateMarketIndex();
  const updateMutation = useUpdateMarketIndex();
  const deleteMutation = useDeleteMarketIndex();

  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [tradingviewUrl, setTradingviewUrl] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editSymbol, setEditSymbol] = useState("");
  const [editName, setEditName] = useState("");
  const [editTradingviewUrl, setEditTradingviewUrl] = useState("");

  function handleCreate() {
    const payload: MarketIndexDefinitionCreate = {
      symbol: symbol.trim().toUpperCase(),
      name: name.trim(),
      tradingview_url: tradingviewUrl.trim() || null,
      is_active: true,
    };
    createMutation.mutate(payload, {
      onSuccess: () => {
        setSymbol("");
        setName("");
        setTradingviewUrl("");
      },
    });
  }

  function handleToggleActive(id: string, current: boolean) {
    const payload: MarketIndexDefinitionUpdate = {
      is_active: !current,
    };
    updateMutation.mutate({ id, payload });
  }

  function startEdit(index: MarketIndexDefinitionResponse) {
    setEditingId(index.id);
    setEditSymbol(index.symbol);
    setEditName(index.name);
    setEditTradingviewUrl(index.tradingview_url ?? "");
  }

  function cancelEdit() {
    setEditingId(null);
  }

  function saveEdit(id: string) {
    const payload: MarketIndexDefinitionUpdate = {
      symbol: editSymbol.trim().toUpperCase(),
      name: editName.trim(),
      tradingview_url: editTradingviewUrl.trim() || null,
    };
    updateMutation.mutate(
      { id, payload },
      { onSuccess: () => setEditingId(null) }
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-foreground">MARKET INDEXES</h3>
        <p className="text-xs text-muted-foreground mt-0.5">
          Manage index definitions used in check-ins.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Symbol (e.g. SPX)"
          className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm"
        />
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
          className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm"
        />
        <input
          value={tradingviewUrl}
          onChange={(e) => setTradingviewUrl(e.target.value)}
          placeholder="TradingView URL"
          className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm"
        />
      </div>
      <button
        type="button"
        onClick={handleCreate}
        disabled={createMutation.isPending || !symbol.trim() || !name.trim()}
        className="px-4 py-2 rounded-lg text-sm font-medium bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground transition-colors"
      >
        {createMutation.isPending ? "Creating..." : "Add Market Index"}
      </button>

      {isLoading ? (
        <div className="py-4 text-sm text-muted-foreground">Loading indexes...</div>
      ) : isError ? (
        <div className="py-4 text-sm text-destructive">Could not load market indexes.</div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border">
                <th className="px-4 py-3 text-left">Symbol</th>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">TradingView</th>
                <th className="px-4 py-3 text-center">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {(indexes ?? []).map((index) => (
                <tr key={index.id} className="bg-card hover:bg-muted/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-sm text-muted-foreground">
                    {editingId === index.id ? (
                      <input
                        value={editSymbol}
                        onChange={(e) => setEditSymbol(e.target.value)}
                        className="w-full px-2 py-1 rounded border border-border bg-background text-foreground text-sm"
                      />
                    ) : (
                      index.symbol
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {editingId === index.id ? (
                      <input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-full px-2 py-1 rounded border border-border bg-background text-foreground text-sm"
                      />
                    ) : (
                      index.name
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {editingId === index.id ? (
                      <input
                        value={editTradingviewUrl}
                        onChange={(e) => setEditTradingviewUrl(e.target.value)}
                        className="w-full px-2 py-1 rounded border border-border bg-background text-foreground text-sm"
                      />
                    ) : index.tradingview_url ? (
                      <a
                        href={index.tradingview_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary hover:underline"
                      >
                        Open
                      </a>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <StatusToggle
                      enabled={index.is_active ?? false}
                      onChange={() => handleToggleActive(index.id, index.is_active ?? false)}
                    />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-3">
                      {editingId === index.id ? (
                        <>
                          <button
                            type="button"
                            onClick={() => saveEdit(index.id)}
                            className="text-xs font-medium text-primary hover:underline"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={cancelEdit}
                            className="text-xs text-muted-foreground hover:text-foreground"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => startEdit(index)}
                          className="text-xs font-medium text-muted-foreground hover:text-foreground"
                        >
                          Edit
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => deleteMutation.mutate(index.id)}
                        className="text-xs text-destructive hover:underline"
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
    </div>
  );
}

// ─── Warning Modal ────────────────────────────────────────────────────────────

interface WarningModalProps {
  fieldName: string;
  onConfirm: () => void;
  onCancel: () => void;
  isSubmitting: boolean;
}

function DeactivateMetricWarningModal({ fieldName, onConfirm, onCancel, isSubmitting }: WarningModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-card rounded-xl border border-border shadow-xl p-6 w-full max-w-md mx-4">
        <div className="flex items-start gap-3 mb-4">
          <div className="shrink-0 mt-0.5">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-6 h-6 text-warning">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-foreground">Deactivate &quot;{fieldName}&quot;?</h2>
            <p className="text-sm text-muted-foreground mt-2">
              Historical data for this metric will remain visible, but no new entries will be possible
              for future check-ins. Deactivation does not delete existing records.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium bg-background text-foreground border border-border rounded-md hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-warning hover:bg-warning/90 disabled:opacity-50 text-warning-foreground transition-colors"
          >
            {isSubmitting ? "Deactivating..." : "Deactivate"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Market Phases Section ────────────────────────────────────────────────────

function MarketPhaseSection() {
  const { data: phases, isLoading, isError } = useMarketPhases();
  const createMutation = useCreateMarketPhase();
  const updateMutation = useUpdateMarketPhase();

  const [showAddModal, setShowAddModal] = useState(false);
  const [addForm, setAddForm] = useState<PhaseFormState>(EMPTY_PHASE_FORM);
  const [addError, setAddError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState("");
  const [editColor, setEditColor] = useState("");

  function handleAdd() {
    const keyError = validatePhaseKey(addForm.name);
    if (keyError) { setAddError(keyError); return; }
    const labelError = validatePhaseLabel(addForm.label);
    if (labelError) { setAddError(labelError); return; }
    setAddError(null);

    const payload: MarketPhaseDefinitionCreate = {
      name: addForm.name.trim().toLowerCase(),
      label: addForm.label.trim(),
      color_hex: addForm.color_hex,
    };

    createMutation.mutate(payload, {
      onSuccess: () => {
        setShowAddModal(false);
        setAddForm(EMPTY_PHASE_FORM);
      },
      onError: (err) => {
        setAddError(err.message ?? "Failed to create market phase.");
      },
    });
  }

  function startEdit(phase: MarketPhaseDefinitionRead) {
    setEditingId(phase.id);
    setEditLabel(phase.label);
    setEditColor(phase.color_hex);
  }

  function cancelEdit() {
    setEditingId(null);
  }

  function saveEdit(phaseId: string) {
    const labelError = validatePhaseLabel(editLabel);
    if (labelError) return;
    const payload: MarketPhaseDefinitionUpdate = {
      label: editLabel.trim(),
      color_hex: editColor,
    };
    updateMutation.mutate(
      { id: phaseId, payload },
      {
        onSuccess: () => setEditingId(null),
      }
    );
  }

  function toggleActive(phaseId: string, current: boolean) {
    updateMutation.mutate({
      id: phaseId,
      payload: { is_active: !current },
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">MARKET PHASES</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Define market phases (e.g. bullish, bearish) for check-in entries.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setAddForm(EMPTY_PHASE_FORM);
            setAddError(null);
            setShowAddModal(true);
          }}
          className="shrink-0 ml-4 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-primary hover:bg-primary/90 text-primary-foreground transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          + New Phase
        </button>
      </div>

      {isLoading ? (
        <div className="py-10 text-center text-sm text-muted-foreground">Loading...</div>
      ) : isError ? (
        <div className="py-10 text-center rounded-xl border border-dashed border-destructive/30 bg-[color-mix(in_srgb,hsl(var(--destructive))_10%,transparent)] text-sm text-destructive px-6">
          <p className="font-medium">Could not load market phases.</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Check your connection and try refreshing the page.
          </p>
        </div>
      ) : !phases || phases.length === 0 ? (
        <div className="py-10 text-center rounded-xl border border-dashed border-border text-muted-foreground text-sm">
          No market phases defined yet.{" "}
          <button
            type="button"
            onClick={() => {
              setAddForm(EMPTY_PHASE_FORM);
              setAddError(null);
              setShowAddModal(true);
            }}
            className="text-primary hover:underline"
          >
            Add your first phase.
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border">
                <th className="px-4 py-3 text-left w-1/4">Key</th>
                <th className="px-4 py-3 text-left w-1/4">Label</th>
                <th className="px-4 py-3 text-left w-1/4">Color</th>
                <th className="px-4 py-3 text-center w-1/4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {phases.map((phase) => {
                const isEditing = editingId === phase.id;
                return (
                  <tr key={phase.id} className="bg-card hover:bg-muted/50 transition-colors">
                    {/* Key — immutable */}
                    <td className="px-4 py-3 font-mono text-sm text-muted-foreground">
                      {phase.name}
                    </td>
                    {/* Label — editable inline */}
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editLabel}
                          onChange={(e) => setEditLabel(e.target.value)}
                          maxLength={100}
                          className="w-full px-2 py-1 rounded border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                      ) : (
                        <span className="text-foreground">{phase.label}</span>
                      )}
                    </td>
                    {/* Color — editable inline */}
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <ColorPickerButton
                          color={editColor}
                          onChange={(c) => setEditColor(c)}
                        />
                      ) : (
                        <span className="inline-flex items-center gap-2">
                          <span
                            className="inline-block w-3.5 h-3.5 rounded-sm border border-border"
                            style={{ backgroundColor: phase.color_hex }}
                          />
                          <span className="text-sm font-mono text-muted-foreground">{phase.color_hex}</span>
                        </span>
                      )}
                    </td>
                    {/* Status + Edit/Save */}
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-3">
                        <StatusToggle
                          enabled={phase.is_active}
                          onChange={() => toggleActive(phase.id, phase.is_active)}
                        />
                        <span className="text-xs text-muted-foreground w-10 text-left">
                          {phase.is_active ? "Active" : "Inactive"}
                        </span>
                        {isEditing ? (
                          <div className="flex items-center gap-1 ml-2">
                            <button
                              type="button"
                              onClick={() => saveEdit(phase.id)}
                              className="text-xs font-medium text-primary hover:underline"
                            >
                              Save
                            </button>
                            <button
                              type="button"
                              onClick={cancelEdit}
                              className="text-xs text-muted-foreground hover:text-foreground"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => startEdit(phase)}
                            className="text-xs font-medium text-muted-foreground hover:text-foreground ml-2"
                          >
                            Edit
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Phase Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card rounded-xl border border-border shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-semibold text-foreground">New Market Phase</h3>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Key <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  value={addForm.name}
                  onChange={(e) => setAddForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. bullish, low-vol"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <p className="text-xs text-muted-foreground mt-1">Lowercase kebab-case, immutable after creation.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Label <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  value={addForm.label}
                  onChange={(e) => setAddForm((f) => ({ ...f, label: e.target.value }))}
                  placeholder="e.g. Bullish"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Color
                </label>
                <ColorPickerButton
                  color={addForm.color_hex}
                  onChange={(c) => setAddForm((f) => ({ ...f, color_hex: c }))}
                />
              </div>
            </div>
            {addError && <p className="mt-3 text-sm text-destructive">{addError}</p>}
            <div className="flex justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-sm font-medium bg-background text-foreground border border-border rounded-md hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAdd}
                disabled={createMutation.isPending}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground transition-colors"
              >
                {createMutation.isPending ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Custom Metrics Section ───────────────────────────────────────────────────

function CustomMetricsSection() {
  const { data: fields, isLoading, isError } = useCheckinFields();
  const createMutation = useCreateCheckinField();
  const updateMutation = useUpdateCheckinField();

  const [showAddModal, setShowAddModal] = useState(false);
  const [addForm, setAddForm] = useState<FieldFormState>(EMPTY_FIELD_FORM);
  const [addError, setAddError] = useState<string | null>(null);

  const [deactivateTarget, setDeactivateTarget] = useState<{
    id: string;
    field_name: string;
  } | null>(null);

  function handleAdd() {
    const keyError = validateFieldKey(addForm.field_name);
    if (keyError) { setAddError(keyError); return; }
    setAddError(null);

    const payload: CheckinFieldDefinitionCreate = {
      field_name: addForm.field_name.trim().toLowerCase(),
      field_type: addForm.field_type,
    };

    createMutation.mutate(payload, {
      onSuccess: () => {
        setShowAddModal(false);
        setAddForm(EMPTY_FIELD_FORM);
      },
      onError: (err) => {
        setAddError(err.message ?? "Failed to create metric.");
      },
    });
  }

  function toggleActive(fieldId: string, current: boolean, fieldName: string) {
    if (current) {
      // Deactivating — show warning modal first
      setDeactivateTarget({ id: fieldId, field_name: fieldName });
    } else {
      // Activating — direct update
      updateMutation.mutate({
        id: fieldId,
        payload: { is_active: true },
      });
    }
  }

  function confirmDeactivate() {
    if (!deactivateTarget) return;
    updateMutation.mutate(
      {
        id: deactivateTarget.id,
        payload: { is_active: false },
      },
      {
        onSuccess: () => setDeactivateTarget(null),
      }
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">CUSTOM METRICS</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Define custom metrics (integer or boolean) for check-in entries.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setAddForm(EMPTY_FIELD_FORM);
            setAddError(null);
            setShowAddModal(true);
          }}
          className="shrink-0 ml-4 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-primary hover:bg-primary/90 text-primary-foreground transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          + New Metric
        </button>
      </div>

      {isLoading ? (
        <div className="py-10 text-center text-sm text-muted-foreground">Loading...</div>
      ) : isError ? (
        <div className="py-10 text-center rounded-xl border border-dashed border-destructive/30 bg-[color-mix(in_srgb,hsl(var(--destructive))_10%,transparent)] text-sm text-destructive px-6">
          <p className="font-medium">Could not load custom metrics.</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Check your connection and try refreshing the page.
          </p>
        </div>
      ) : !fields || fields.length === 0 ? (
        <div className="py-10 text-center rounded-xl border border-dashed border-border text-muted-foreground text-sm">
          No custom metrics defined yet.{" "}
          <button
            type="button"
            onClick={() => {
              setAddForm(EMPTY_FIELD_FORM);
              setAddError(null);
              setShowAddModal(true);
            }}
            className="text-primary hover:underline"
          >
            Add your first metric.
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border">
                <th className="px-4 py-3 text-left w-1/3">Key</th>
                <th className="px-4 py-3 text-left w-1/3">Type</th>
                <th className="px-4 py-3 text-center w-1/3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {fields.map((field) => (
                <tr key={field.id} className="bg-card hover:bg-muted/50 transition-colors">
                  {/* Key — immutable */}
                  <td className="px-4 py-3 font-mono text-sm text-muted-foreground">
                    {field.field_name}
                  </td>
                  {/* Type — immutable */}
                  <td className="px-4 py-3">
                    <FieldTypeBadge fieldType={field.field_type} />
                  </td>
                  {/* Status — toggle */}
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-3">
                      <StatusToggle
                        enabled={field.is_active}
                        onChange={() => toggleActive(field.id, field.is_active, field.field_name)}
                      />
                      <span className="text-xs text-muted-foreground w-10 text-left">
                        {field.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Field Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card rounded-xl border border-border shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-semibold text-foreground">New Custom Metric</h3>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Key <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  value={addForm.field_name}
                  onChange={(e) => setAddForm((f) => ({ ...f, field_name: e.target.value }))}
                  placeholder="e.g. mood-level, focus"
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <p className="text-xs text-muted-foreground mt-1">Lowercase kebab-case, immutable after creation.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Type <span className="text-destructive">*</span>
                </label>
                <select
                  value={addForm.field_type}
                  onChange={(e) => setAddForm((f) => ({ ...f, field_type: e.target.value as FieldTypeEnum }))}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="integer">Integer</option>
                  <option value="boolean">Boolean</option>
                </select>
                <p className="text-xs text-muted-foreground mt-1">Type is immutable after creation.</p>
              </div>
            </div>
            {addError && <p className="mt-3 text-sm text-destructive">{addError}</p>}
            <div className="flex justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-sm font-medium bg-background text-foreground border border-border rounded-md hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAdd}
                disabled={createMutation.isPending}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground transition-colors"
              >
                {createMutation.isPending ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Deactivate Warning Modal */}
      {deactivateTarget !== null && (
        <DeactivateMetricWarningModal
          fieldName={deactivateTarget.field_name}
          onConfirm={confirmDeactivate}
          onCancel={() => setDeactivateTarget(null)}
          isSubmitting={updateMutation.isPending}
        />
      )}
    </div>
  );
}

// ─── Exported component ───────────────────────────────────────────────────────

export function CheckinSettings() {
  return (
    <div className="space-y-8">
      <MarketIndexesSection />
      <div className="border-t border-border" />
      <MarketPhaseSection />
      <div className="border-t border-border" />
      <CustomMetricsSection />
    </div>
  );
}
