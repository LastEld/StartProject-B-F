// src/app/components/AuthGuard.tsx
"use client";

import React, { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "../app/lib/auth";// <= скорректируй путь, если новый хук!
import { Loader2 } from "lucide-react";

interface AuthGuardProps {
  children: React.ReactNode;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Если не грузится и не авторизован, редиректим
    if (!isLoading && !isAuthenticated) {
      const isAuthPage = pathname?.startsWith("/auth/");
      const redirectUrl =
        !isAuthPage && pathname !== "/" ? pathname : "/dashboard";
      // Не сохраняем login/register как точку возврата
      router.push(`/auth/login?redirect=${encodeURIComponent(redirectUrl)}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (isLoading) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-gray-100 dark:bg-gray-900 p-4">
        <Loader2 className="w-12 h-12 animate-spin text-blue-500 dark:text-blue-400" />
        <p className="mt-4 text-lg text-gray-700 dark:text-gray-300">
          Checking authentication...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Быстрый лоадер во время редиректа
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-gray-100 dark:bg-gray-900 p-4">
        <Loader2 className="w-12 h-12 animate-spin text-red-500 dark:text-red-400" />
        <p className="mt-4 text-lg text-gray-700 dark:text-gray-300">
          Redirecting to login...
        </p>
      </div>
    );
  }

  // Если все ок — показываем защищенный контент
  return <>{children}</>;
};

export default AuthGuard;
