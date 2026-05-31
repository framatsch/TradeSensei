import { icons } from "lucide-react";
import type { LucideProps } from "lucide-react";

interface DynamicIconProps extends Omit<LucideProps, "ref"> {
  name?: string | null;
  fallback?: keyof typeof icons;
}

export function DynamicIcon({ name, fallback = "Tag", ...props }: DynamicIconProps) {
  let IconComponent = icons[fallback];

  if (name) {
    // Convert name (e.g. "alert-circle" or "alertCircle") to Component name (e.g. "AlertCircle")
    // Note: lucide-react exports icons in PascalCase
    const formattedName = name
      .replace(/^lucide:/, "") // Sometimes prefixes are added
      .split("-")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join("");

    if (formattedName in icons) {
      IconComponent = icons[formattedName as keyof typeof icons];
    }
  }

  if (!IconComponent) {
    return null;
  }

  return <IconComponent {...props} />;
}
