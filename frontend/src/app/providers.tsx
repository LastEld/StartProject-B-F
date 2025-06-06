//app/providers.tsx
"use client";

import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
// import { ReactQueryDevtools } from "@tanstack/react-query-devtools"; // опционально

// Глобальный singleton-клиент только для браузера
let browserQueryClient: QueryClient | undefined = undefined;

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 минута
        // gcTime: 1000 * 60 * 60 * 24, // 24 часа, если понадобится
      },
    },
  });
}

function getQueryClient() {
  if (typeof window === "undefined") {
    // SSR: всегда новый
    return makeQueryClient();
  } else {
    // CSR: singleton на всё приложение
    if (!browserQueryClient) browserQueryClient = makeQueryClient();
    return browserQueryClient;
  }
}

// Теперь поддержка вложенных провайдеров (AuthProvider, ThemeProvider и т.д.)
import { AuthProvider } from "@/app/lib/auth"; // путь под себя

export default function AppProviders({ children }: { children: React.ReactNode }) {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {children}
      </AuthProvider>
      {/* <ReactQueryDevtools initialIsOpen={false} /> */}
    </QueryClientProvider>
  );
}
