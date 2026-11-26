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

import { useState } from "react";
import { Logo } from "@/components/ui/Logo";
import { AboutModal } from "@/components/ui/AboutModal";

export function LoginHeader() {
  const [isAboutOpen, setIsAboutOpen] = useState(false);

  return (
    <div className="flex flex-col items-center gap-3 text-center">
      <button
        type="button"
        onClick={() => setIsAboutOpen(true)}
        className="focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-2xl transition-transform hover:scale-105 active:scale-95 border-none bg-transparent p-0 cursor-pointer"
        aria-label="About Trade Sensei"
      >
        <Logo size={72} className="rounded-2xl" />
      </button>
      <h1 className="text-2xl font-semibold text-foreground">Sign in to Trade Sensei</h1>
      <AboutModal
        isOpen={isAboutOpen}
        onClose={() => setIsAboutOpen(false)}
        version={process.env.NEXT_PUBLIC_APP_VERSION}
      />
    </div>
  );
}
