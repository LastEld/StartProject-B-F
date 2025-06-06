//src\app\components\Sidebar.tsx
// src/app/components/Sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home, LayoutDashboard, Settings, Users, FileStack, Brain, Plug,
  ListChecks, ClipboardList, UserCog
} from "lucide-react";
import { useAuth } from "@/app/lib/auth"; // Новый путь к useAuth

const baseNavLinks = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FileStack },
  { href: "/tasks", label: "Tasks", icon: ClipboardList },
  { href: "/devlog", label: "DevLog", icon: ListChecks },
  { href: "/teams", label: "Teams", icon: Users },
  { href: "/plugins", label: "Plugins", icon: Plug },
  { href: "/templates", label: "Templates", icon: FileStack },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/jarvis", label: "Jarvis", icon: Brain },
];
const adminNavLinks = [
  { href: "/users", label: "User Management", icon: UserCog },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, isAuthenticated } = useAuth();

  // isAdmin определяем по флагу is_superuser или ролям
  const isAdmin = user?.is_superuser || (user?.roles?.includes("admin"));

  // Sidebar не показываем на страницах /auth/*
  if (pathname.startsWith("/auth")) return null;

  // Формируем список ссылок (добавляем admin ссылки после "Teams")
  let linksToShow = baseNavLinks;
  if (isAuthenticated && isAdmin) {
    const teamsIndex = linksToShow.findIndex(link => link.href === "/teams");
    if (teamsIndex !== -1) {
      linksToShow = [
        ...linksToShow.slice(0, teamsIndex + 1),
        ...adminNavLinks,
        ...linksToShow.slice(teamsIndex + 1)
      ];
    } else {
      linksToShow = [...linksToShow, ...adminNavLinks];
    }
  }

  return (
    <aside className="w-64 min-h-screen bg-zinc-900 border-r border-zinc-800 flex flex-col py-6 px-2">
      <div className="flex items-center gap-2 px-4 pb-8">
        <Home className="w-6 h-6 text-blue-400" />
        <span className="font-bold text-lg text-white">DevOS Jarvis</span>
      </div>
      <nav className="flex flex-col gap-1">
        {linksToShow.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
              pathname === href
                ? "bg-blue-950 text-blue-300"
                : "text-zinc-300 hover:bg-zinc-800"
            }`}
          >
            <Icon className="w-5 h-5" />
            <span>{label}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
