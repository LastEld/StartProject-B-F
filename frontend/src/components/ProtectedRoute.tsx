//app/components/ProtectedRoute.tsx
"use client";

import React, { ReactNode, useEffect } from "react";
import { useAuth } from "@/app/lib/auth"; // или "../lib/auth" если структура другая
import { useRouter } from "next/navigation";
import { Loader2, Lock } from "lucide-react";

/**
 * Props:
 * - children: ReactNode (вложенный контент)
 * - requireAdmin?: boolean (ограничить только для админа)
 */
type ProtectedRouteProps = {
  children: ReactNode;
  requireAdmin?: boolean;
};

/**
 * Компонент, который блокирует доступ к children если не авторизован,
 * либо не является админом (если requireAdmin=true).
 */
export default function ProtectedRoute({
  children,
  requireAdmin = false,
}: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  // Проверка доступа
  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.replace("/auth/login");
      } else if (requireAdmin && !user?.is_superuser) {
        router.replace("/dashboard"); // или другая страница для "нет доступа"
      }
    }
  }, [isAuthenticated, isLoading, user, requireAdmin, router]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-3" />
        <span className="text-lg text-gray-600 dark:text-gray-300">
          Checking access...
        </span>
      </div>
    );
  }

  // Уже авторизован (и если надо — проверен на роль)
  if (!isAuthenticated) {
    // На всякий случай можно рендерить скелетон
    return null;
  }
  if (requireAdmin && !user?.is_superuser) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <Lock className="w-8 h-8 text-red-500 mb-3" />
        <span className="text-lg text-gray-600 dark:text-gray-300">
          Access denied. Admins only.
        </span>
      </div>
    );
  }

  return <>{children}</>;
}
