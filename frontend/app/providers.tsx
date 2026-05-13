"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState, useEffect } from "react";
import { useAppContextStore } from "@/stores/appContextStore";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { registerApiInterceptors } from "@/lib/apiInterceptors";

// Register JWT injection + 401 → logout interceptors at module scope so they are
// active before TanStack Query fires its first requests on mount.
// SSR-safe: registerApiInterceptors() no-ops when typeof window === "undefined".
// Idempotent: the interceptorsRegistered module flag prevents double-registration.
registerApiInterceptors();

interface Props {
  children: React.ReactNode;
}

export function Providers({ children }: Props) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            retry: 1,
          },
        },
      })
  );

  useEffect(() => {
    useAppContextStore.getState().hydrate();
    usePortfolioStore.getState().hydrate();
  }, []);

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </ThemeProvider>
  );
}
