//app/users/new/page.tsx
"use client";

import React, { useState, ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createUser } from "@/app/lib/api"; // Обычно createUser, не registerUser!
import type { UserCreate } from "@/app/lib/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { AlertCircle, Loader2, UserPlus, ArrowLeft } from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";

import { useAuth } from "@/app/lib/useAuth"; // Используй реальный хук!

const initialFormData: UserCreate = {
  username: "",
  email: "",
  password: "",
  full_name: "",
  roles: ["user"], // массив, как в твоих типах!
  is_active: true,        // по умолчанию новый пользователь активен
  is_superuser: false,    // по умолчанию НЕ суперюзер
};

export default function RegisterUserPage() {
  const router = useRouter();
  const { user: currentUser, isAuthenticated } = useAuth();
  const isAdmin = !!currentUser?.is_superuser; // определяем по твоим данным
  const [formData, setFormData] = useState<UserCreate>(initialFormData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleRoleChange = (value: string) => {
    if (isAdmin) {
      setFormData(prev => ({ ...prev, roles: [value] })); // roles это массив
    }
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!formData.username.trim()) { setError("Username is required."); return; }
    if (!formData.email.trim()) { setError("Email is required."); return; }
    if (!formData.password?.trim()) { setError("Password is required."); return; }
    if (formData.password !== confirmPassword) { setError("Passwords do not match."); return; }
    setIsLoading(true);
    setError(null);

    try {
      let dataToSubmit: UserCreate = { ...formData };
      if (!isAdmin) dataToSubmit.roles = ["user"]; // для публичной регистрации

      const newUser = await createUser(dataToSubmit, isAdmin ? undefined : undefined); // токен не нужен, useAuth всё сам подхватит

      if (newUser && newUser.id) {
        if (isAdmin) {
          router.push(`/users/${newUser.id}`);
        } else {
          router.push("/login");
        }
      } else {
        router.push(isAdmin ? "/users" : "/login");
      }
    } catch (err: any) {
      setError(err?.error?.message || err?.message || "An unknown error occurred during registration.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-md py-12 px-4">
      {isAdmin && (
        <Button onClick={() => router.push("/users")} variant="outline" size="sm" className="mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />Назад к списку
        </Button>
      )}
      <h1 className="text-3xl font-bold mb-8 text-center flex items-center justify-center">
        <UserPlus className="w-8 h-8 mr-3 text-cyan-500" /> {isAdmin ? "Создать пользователя" : "Регистрация"}
      </h1>

      {error && (
        <div className="mb-6 p-3 bg-red-100 text-red-700 border border-red-300 rounded-md flex items-center shadow-sm">
          <AlertCircle className="w-5 h-5 mr-2.5" /> <p className="text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5 bg-white p-8 rounded-xl shadow-xl border">
        <div>
          <Label htmlFor="username" className="mb-1 block">Username <span className="text-red-500">*</span></Label>
          <Input id="username" name="username" value={formData.username} onChange={handleChange} required disabled={isLoading} />
        </div>
        <div>
          <Label htmlFor="email" className="mb-1 block">Email <span className="text-red-500">*</span></Label>
          <Input id="email" name="email" type="email" value={formData.email} onChange={handleChange} required disabled={isLoading} />
        </div>
        <div>
          <Label htmlFor="full_name" className="mb-1 block">Full Name</Label>
          <Input id="full_name" name="full_name" value={formData.full_name || ""} onChange={handleChange} disabled={isLoading} />
        </div>
        <div>
          <Label htmlFor="password" className="mb-1 block">Password <span className="text-red-500">*</span></Label>
          <Input id="password" name="password" type="password" value={formData.password || ""} onChange={handleChange} required disabled={isLoading} />
        </div>
        <div>
          <Label htmlFor="confirmPassword" className="mb-1 block">Confirm Password <span className="text-red-500">*</span></Label>
          <Input id="confirmPassword" name="confirmPassword" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required disabled={isLoading} />
        </div>

        {isAdmin && (
          <div>
            <Label htmlFor="role" className="mb-1 block">Role</Label>
            <Select name="role" value={formData.roles?.[0] || "user"} onValueChange={handleRoleChange} disabled={isLoading}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="user">User</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
                {/* Другие роли — если есть */}
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="pt-3">
          <Button type="submit" className="w-full bg-cyan-500 hover:bg-cyan-600 text-white font-semibold py-3 text-lg rounded-md" disabled={isLoading}>
            {isLoading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <UserPlus className="mr-2 h-5 w-5" />}
            disabled={isLoading}
            {isLoading ? (
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            ) : (
              <UserPlus className="mr-2 h-5 w-5" />
            )}
            {isLoading
              ? isAdmin
                ? "Создаём..."
                : "Регистрируем..."
              : isAdmin
                ? "Создать пользователя"
                : "Зарегистрироваться"}
          </Button>
        </div>
      </form>
    </div>
  );
}