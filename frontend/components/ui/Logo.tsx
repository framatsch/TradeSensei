/**
 * Logo component — renders the project logo.svg at configurable sizes.
 * The SVG has a dark square background (#050a0a) with a 512×512 viewBox,
 * so we render it as a rounded square to match the existing icon style.
 */

import Image from "next/image";

interface LogoProps {
  /** Side length in pixels (the logo is always square). Defaults to 32. */
  size?: number;
  /** Extra Tailwind classes applied to the wrapper div. */
  className?: string;
}

export function Logo({ size = 32, className = "" }: LogoProps) {
  return (
    <div
      className={`flex-shrink-0 rounded-lg overflow-hidden border border-border ${className}`}
      style={{ width: size, height: size }}
    >
      <Image
        src="/logo.svg"
        alt="Trade Sensei logo"
        width={size}
        height={size}
        priority
        style={{ display: "block", width: size, height: size }}
      />
    </div>
  );
}
