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

import { create } from 'zustand';

export type AppContext = 'portfolio' | 'library' | 'checkin' | 'none';

export interface AppContextState {
  activeContext: AppContext;
  hydrated: boolean;
  setActiveContext: (ctx: AppContext) => void;
  hydrate: () => void;
}

const isValidContext = (ctx: any): ctx is AppContext => {
  return ['portfolio', 'library', 'checkin', 'none'].includes(ctx);
};

export const useAppContextStore = create<AppContextState>((set) => ({
  activeContext: 'portfolio',
  hydrated: false,
  setActiveContext: (ctx: AppContext) => {
    set({ activeContext: ctx });
    // Don't persist 'none' so that returning to the app defaults back to real context
    if (ctx !== 'none') {
      try {
        localStorage.setItem('active_app_context', ctx);
      } catch (err) {
        console.error('Failed to save active_app_context to localStorage', err);
      }
    }
  },
  hydrate: () => {
    let context: AppContext = 'portfolio';
    try {
      const stored = localStorage.getItem('active_app_context');
      if (isValidContext(stored)) {
        context = stored;
      } else {
        // Invalid or missing value — normalize to default and persist it
        localStorage.setItem('active_app_context', context);
      }
    } catch (err) {
      console.error('Failed to read active_app_context from localStorage', err);
    }
    set({ activeContext: context, hydrated: true });
  },
}));
