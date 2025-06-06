//src/app/auth/login/page.tsx
"use client";

import React, { useState, FormEvent, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/app/lib/auth";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AlertCircle, Loader2, LogIn } from "lucide-react";
import Link from "next/link";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { login, isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated && user) {
      router.push("/dashboard");
    }
  }, [isAuthenticated, user, router]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    if (!username || !password) {
      setError("Both username and password are required.");
      return;
    }
    try {
      await login(username, password);
      // Редирект — useEffect
    } catch (err: any) {
      setError(err.message || "Login failed. An unknown error occurred.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-gray-100 dark:bg-gray-900 p-4">
        <Loader2 className="w-12 h-12 animate-spin text-blue-500 dark:text-blue-400" />
        <p className="mt-4 text-lg text-gray-700 dark:text-gray-300">
          Loading authentication state...
        </p>
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen bg-gray-100 dark:bg-gray-900 p-4">
        <Loader2 className="w-12 h-12 animate-spin text-blue-500 dark:text-blue-400" />
        <p className="mt-4 text-lg text-gray-700 dark:text-gray-300">
          Redirecting...
        </p>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 to-gray-900 p-4">
      <Card className="w-full max-w-md bg-white dark:bg-gray-800 shadow-2xl rounded-xl border dark:border-gray-700">
        <CardHeader className="text-center space-y-2 pt-8">
          <LogIn className="w-12 h-12 mx-auto text-blue-500 dark:text-blue-400" />
          <CardTitle className="text-3xl font-bold text-gray-800 dark:text-white">
            Welcome Back!
          </CardTitle>
          <CardDescription className="text-gray-600 dark:text-gray-400">
            Sign in to access your DevOS Jarvis dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-8 py-6 space-y-6">
          {error && (
            <div className="p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-md flex items-center text-sm shadow">
              <AlertCircle className="w-5 h-5 mr-2.5 flex-shrink-0" />
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-1.5">
              <Label
                htmlFor="username"
                className="text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Username or Email
              </Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="your_username or email@example.com"
                required
                className="dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:ring-blue-500 focus:border-blue-500"
                disabled={isLoading}
              />
            </div>
            <div className="space-y-1.5">
              <Label
                htmlFor="password"
                className="text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="dark:bg-gray-700 dark:border-gray-600 dark:text-white focus:ring-blue-500 focus:border-blue-500"
                disabled={isLoading}
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white font-semibold py-3 text-lg rounded-md shadow-md hover:shadow-lg transition-all duration-150 ease-in-out"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              ) : (
                <LogIn className="mr-2 h-5 w-5" />
              )}
              {isLoading ? "Signing In..." : "Sign In"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="px-8 pb-8 text-center block">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Don&apos;t have an account?{" "}
            <Link href="/auth/register" legacyBehavior>
              <a className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 underline">
                Create one here
              </a>
            </Link>
          </p>
          <p className="mt-3 text-xs text-gray-500 dark:text-gray-500">
            <Link href="/auth/forgot-password" legacyBehavior>
              <a className="hover:underline">Forgot your password?</a>
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
