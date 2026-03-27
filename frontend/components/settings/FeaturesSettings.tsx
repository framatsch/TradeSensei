"use client";

import React from "react";
import { FEATURE_FLAGS } from "@/lib/featureFlags";
import useFeatureFlag from "@/hooks/useFeatureFlag";
import { useUpdateSettings, useSettings } from "@/hooks/useSettings";

export default function FeaturesSettings() {
  const { data: settings } = useSettings();
  const update = useUpdateSettings();

  const onToggle = (key: string, value: boolean) => {
    update.mutate({ features: { [key]: value } });
  };

  return (
    <div className="space-y-3 mt-4">
      <h3 className="text-sm font-semibold text-slate-600">Features</h3>
      <div className="space-y-2">
        {FEATURE_FLAGS.map((f) => {
          const enabled = (settings as any)?.features?.[f.key] ?? false;
          return (
            <div key={f.key} className="flex items-center justify-between p-2 border rounded">
              <div>
                <div className="font-medium">{f.label}</div>
                <div className="text-xs text-slate-500">{f.description}</div>
              </div>
              <div>
                <label className="inline-flex items-center">
                  <input
                    type="checkbox"
                    className="form-checkbox"
                    checked={enabled}
                    onChange={(e) => onToggle(f.key, e.target.checked)}
                    disabled={f.comingSoon}
                  />
                </label>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
