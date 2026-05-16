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
import Link from "next/link";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Settings, HelpCircle, Info, LogOut } from "lucide-react";
import { useCurrentUser, useLogout } from "@/hooks/useAuth";
import { AboutModal } from "@/components/ui/AboutModal";

function getInitials(username?: string, email?: string) {
  if (username) {
    const parts = username.trim().split(' ');
    if (parts.length >= 2) {
      return `${parts[0].charAt(0)}${parts[parts.length - 1].charAt(0)}`.toUpperCase();
    }
    return username.substring(0, 2).toUpperCase();
  }
  if (email) {
    return email.substring(0, 2).toUpperCase();
  }
  return "U";
}

function getAvatarColor(id?: string) {
  if (!id) return "hsl(0, 65%, 48%)";
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  return `hsl(${Math.abs(hash) % 360}, 65%, 48%)`;
}

export function UserBadge() {
  const { data: user, isLoading } = useCurrentUser();
  const { mutate: logout } = useLogout();
  const [aboutOpen, setAboutOpen] = useState(false);

  if (isLoading || !user) {
    return <div className="w-8 h-8 rounded-full bg-muted animate-pulse" />;
  }

  const initials = getInitials(user.username, user.email);
  const bgColor = getAvatarColor(user.id);
  const version = process.env.NEXT_PUBLIC_APP_VERSION || "0.26.1";

  return (
    <>
      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          <button
            className="flex items-center justify-center w-8 h-8 rounded-full text-white text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring hover:opacity-90 transition-opacity"
            style={{ backgroundColor: bgColor }}
            aria-label="User menu"
          >
            {initials}
          </button>
        </DropdownMenu.Trigger>

        <DropdownMenu.Portal>
          <DropdownMenu.Content
            align="end"
            sideOffset={8}
            className="z-50 w-56 p-1 bg-popover border border-border rounded-md shadow-md text-popover-foreground outline-none animate-in fade-in-80 zoom-in-95 data-[side=bottom]:slide-in-from-top-2"
          >
            <div className="px-2 py-2 border-b border-border/50 mb-1">
              <p className="text-sm font-medium truncate">
                {user.username || user.email}
              </p>
              <p className="text-xs text-muted-foreground truncate">{user.email}</p>
            </div>

            <DropdownMenu.Item asChild>
              <Link
                href="/dashboard/settings"
                className="flex items-center w-full p-2 text-sm rounded-sm outline-none cursor-pointer hover:bg-muted focus:bg-muted"
              >
                <Settings className="w-4 h-4 mr-2 text-muted-foreground" />
                Settings
              </Link>
            </DropdownMenu.Item>

            <DropdownMenu.Item
              onClick={() => window.open("/help", "_blank")}
              className="flex items-center w-full p-2 text-sm rounded-sm outline-none cursor-pointer hover:bg-muted focus:bg-muted"
            >
              <HelpCircle className="w-4 h-4 mr-2 text-muted-foreground" />
              Help
            </DropdownMenu.Item>

            <DropdownMenu.Item
              onClick={() => setAboutOpen(true)}
              className="flex items-center w-full p-2 text-sm rounded-sm outline-none cursor-pointer hover:bg-muted focus:bg-muted"
            >
              <Info className="w-4 h-4 mr-2 text-muted-foreground" />
              About
            </DropdownMenu.Item>

            <DropdownMenu.Separator className="h-px bg-border/50 my-1" />

            <DropdownMenu.Item
              onClick={() => logout()}
              className="flex items-center w-full p-2 text-sm text-red-600 dark:text-red-400 rounded-sm outline-none cursor-pointer hover:bg-red-500/10 focus:bg-red-500/10"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Sign Out
            </DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>

      <AboutModal
        isOpen={aboutOpen}
        onClose={() => setAboutOpen(false)}
        version={version}
      />
    </>
  );
}
