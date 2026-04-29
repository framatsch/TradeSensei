"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState, useEffect } from "react";
import { useAppContextStore } from "@/stores/appContextStore";
import { usePortfolioStore } from "@/stores/portfolioStore";
import { initializeApiClient } from "@/lib/api/init";

// Configure the @hey-api SDK once at module load (base URL + JWT interceptors)
initializeApiClient();

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
