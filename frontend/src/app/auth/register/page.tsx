//app/auth/register/page.tsx
"use client";

import React, { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { AlertCircle, UserPlus, Loader2 } from "lucide-react";
import Link from "next/link";
import { createUser } from "@/app/lib/api";
import type { UserCreate } from "@/app/lib/types";

export default function RegisterPage() {
  const [form, setForm] = useState<UserCreate>({
    username: "",
    email: "",
    full_name: "",
    password: "",
    is_active: true,
    is_superuser: false,
    roles: [],
  });
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const router = useRouter();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Simple validation
    if (!form.username || !form.email || !form.password || !confirmPassword) {
      setError("All fields are required.");
      return;
    }
    if (form.password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    try {
      await createUser(form);
      setSuccess("Account created! You can log in.");
      setTimeout(() => {
        router.push("/auth/login");
      }, 1500);
    } catch (err: any) {
      setError(err?.message || "Registration failed. Try another username or email.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 to-gray-900 p-4">
      <Card className="w-full max-w-md bg-white dark:bg-gray-800 shadow-2xl rounded-xl border dark:border-gray-700">
        <CardHeader className="text-center space-y-2 pt-8">
          <UserPlus className="w-12 h-12 mx-auto text-blue-500 dark:text-blue-400" />
          <CardTitle className="text-3xl font-bold text-gray-800 dark:text-white">Create Account</CardTitle>
          <CardDescription className="text-gray-600 dark:text-gray-400">
            Register to use DevOS Jarvis platform.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-8 py-6 space-y-6">
          {error && (
            <div className="p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-md flex items-center text-sm shadow">
              <AlertCircle className="w-5 h-5 mr-2.5 flex-shrink-0" />
              {error}
            </div>
          )}
          {success && (
            <div className="p-3 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border border-green-300 dark:border-green-700 rounded-md flex items-center text-sm shadow">
              <UserPlus className="w-5 h-5 mr-2.5 flex-shrink-0" />
              {success}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-1.5">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                name="username"
                autoComplete="username"
                value={form.username}
                onChange={handleChange}
                required
                disabled={isLoading}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={handleChange}
                required
                disabled={isLoading}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                name="full_name"
                autoComplete="name"
                value={form.full_name || ""}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={form.password}
                onChange={handleChange}
                required
                disabled={isLoading}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
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
                <UserPlus className="mr-2 h-5 w-5" />
              )}
              {isLoading ? "Registering..." : "Create Account"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="px-8 pb-8 text-center block">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Already have an account?{" "}
            <Link href="/auth/login" legacyBehavior>
              <a className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 underline">
                Sign in
              </a>
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
