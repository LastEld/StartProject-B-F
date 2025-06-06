//app\AppShell.tsx
// src/app/AppShell.tsx
"use client";

import Header from "../components/Header";
import Sidebar from "../components/Sidebar";
import { useAuth } from "../app/lib/auth"; // Твой актуальный хук (убедиcь что путь совпадает!)
import AuthGuard from "../components/AuthGuard";
import { usePathname } from "next/navigation";

// Укажи список public-маршрутов, которые не требуют sidebar/header/auth
const PUBLIC_PATHS = [
  "/auth/login",
  "/auth/register",
  "/auth/forgot-password"
  // Добавь сюда и другие public-страницы по необходимости
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublicPath = PUBLIC_PATHS.includes(pathname);

  // Если текущий путь публичный — рендер без обёртки (никаких sidebar/header/auth)
  if (isPublicPath) {
    return <>{children}</>;
  }

  // Все остальные — защищённая оболочка
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900">
        <Header />
        {/* AuthGuard защищает children — внутри main */}
        <AuthGuard>
          <main className="p-4 sm:p-6 lg:p-8 flex-grow">
            {/* Глобальные фичи можно добавить прямо сюда — или сделать гибко через props */}
            {/* <NotificationCenter /> */}
            {/* <JarvisPanel /> */}
            {children}
          </main>
        </AuthGuard>
      </div>
    </div>
  );
}
