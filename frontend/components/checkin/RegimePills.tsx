"use client";

import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { useCheckinParams } from "@/hooks/useCheckinParams";

export function RegimePills() {
  const { data: phases } = useGetTaxonomies("checkins");
  const { regime, setRegime } = useCheckinParams();

  const activePhases = phases ?? [];

  if (activePhases.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {activePhases.map((phase) => {
        const isActive = regime === phase.name;
        return (
          <button
            key={phase.id}
            onClick={() => setRegime(isActive ? null : phase.name)}
            className={`px-3 py-1 text-sm font-medium rounded-full border transition-colors ${
              isActive
                ? "bg-muted text-foreground"
                : "bg-transparent text-muted-foreground hover:text-foreground hover:bg-muted/50"
            }`}
            style={{
              borderColor: isActive ? phase.color_hex : `${phase.color_hex}40`,
            }}
          >
            {phase.name}
          </button>
        );
      })}
    </div>
  );
}
