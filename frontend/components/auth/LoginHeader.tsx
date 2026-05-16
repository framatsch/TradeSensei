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
import Image from "next/image";
import { AboutModal } from "@/components/ui/AboutModal";

export function LoginHeader() {
  const [isAboutOpen, setIsAboutOpen] = useState(false);

  return (
    <div className="flex flex-col items-center mb-8">
      <button
        type="button"
        onClick={() => setIsAboutOpen(true)}
        className="focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-xl transition-transform hover:scale-105 active:scale-95 border-none bg-transparent p-0 cursor-pointer"
        aria-label="About Trade Sensei"
      >
        <Image
          src="/logo.svg"
          alt="Trade Sensei logo"
          width={512}
          height={512}
          priority
          className="rounded-xl mb-4"
          style={{ width: "auto", maxWidth: "100%", height: "auto", maxHeight: "10rem" }}
        />
      </button>
      <h1 className="text-2xl font-bold text-foreground mb-1 tracking-tight">Trade Sensei</h1>
      <p className="text-muted-foreground text-sm">
        Sign in to your account
      </p>
      {/* About Modal */}
      <AboutModal
        isOpen={isAboutOpen}
        onClose={() => setIsAboutOpen(false)}
        version={process.env.NEXT_PUBLIC_APP_VERSION}
      />
    </div>
  );
}