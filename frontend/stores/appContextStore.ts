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
    console.log("setActiveContext called with", ctx);
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
