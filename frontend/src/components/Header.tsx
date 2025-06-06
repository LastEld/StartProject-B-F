
// src/app/components/Header.tsx
// src/app/components/Header.tsx
"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "../app/lib/auth"; // Или путь к твоему AuthProvider/useAuth
import { Button } from "./ui/button";
import { LogOut, UserCircle, Loader2 } from "lucide-react";

const Header: React.FC = () => {
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    // Редирект происходит внутри logout, если надо
  };

  return (
    <header className="w-full flex items-center justify-between py-3 px-6 bg-white dark:bg-gray-800 text-gray-700 dark:text-white shadow-sm border-b dark:border-gray-700">
      <div className="flex items-center gap-3">
        <Link href="/dashboard" legacyBehavior>
          <a className="font-bold text-xl tracking-tight hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
            DevOS Jarvis
          </a>
        </Link>
      </div>
      <div className="flex items-center gap-4">
        {isLoading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : isAuthenticated && user ? (
          <>
            <Link href="/profile" legacyBehavior>
              <a className="flex items-center gap-2 text-sm hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                <UserCircle className="w-5 h-5" />
                {user.username || user.full_name || "Profile"}
              </a>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400"
            >
              <LogOut className="w-4 h-4 mr-1.5" />
              Logout
            </Button>
          </>
        ) : (
          <>
            <Link href="/auth/login" legacyBehavior>
              <Button variant="outline" size="sm" className="dark:border-gray-600 dark:hover:bg-gray-700">
                Login
              </Button>
            </Link>
            <Link href="/auth/register" legacyBehavior>
              <Button size="sm" className="bg-blue-500 hover:bg-blue-600 text-white">
                Sign Up
              </Button>
            </Link>
          </>
        )}
      </div>
    </header>
  );
};

export default Header;
