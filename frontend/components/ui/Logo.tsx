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
