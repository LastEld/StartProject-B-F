//app/lib/useAuth.ts
"use client";

import { useContext } from "react";
import { AuthContext } from "./auth";

// Тип совпадает с твоим AuthContextValue
import type { AuthContextValue } from "./auth";

/**
 * useAuth — удобный хук для доступа к авторизационному контексту.
 * Гарантирует типизацию, автокомплит, выброс ошибки вне провайдера.
 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
