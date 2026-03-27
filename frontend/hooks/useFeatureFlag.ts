"use client";

import { useQueryClient } from "@tanstack/react-query";
import { FeatureFlagKey } from "@/lib/featureFlags";
import { SETTINGS_QUERY_KEY } from "@/hooks/useSettings";

export default function useFeatureFlag(key: FeatureFlagKey): boolean {
  const qc = useQueryClient();
  const settings = qc.getQueryData(SETTINGS_QUERY_KEY) as any | undefined;
  if (!settings) return false;
  const features = settings.features ?? {};
  return Boolean(features?.[key]);
}
