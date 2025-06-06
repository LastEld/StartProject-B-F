//app/users/page.tsx
"use client";

import React, { useEffect, useState, useCallback } from "react";
import { listUsers, updateUser, deleteUser } from "@/app/lib/api";
import type { UserRead } from "@/app/lib/types";
import Link from "next/link";
import { useAuth } from "@/app/lib/useAuth";
import { PlusCircle, Users2, Search, X, Edit3, Trash2, CheckCircle, XCircle, Loader2, AlertCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";

const formatDate = (dateString?: string | null) => {
  if (!dateString) return "—";
  try {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour:'2-digit', minute:'2-digit'
    });
  } catch { return "Invalid Date"; }
};

type UserFilters = {
  search?: string;
  role?: string;
  is_active?: boolean;
};

export default function UsersListPage() {
  const [users, setUsers] = useState<UserRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<UserFilters>({
    search: "",
    role: "",
    is_active: undefined,
  });

  const { user: currentUser } = useAuth();
  const isAdmin = !!currentUser?.is_superuser;

  // API: listUsers поддерживает фильтры и токен автоматически
  const fetchUsers = useCallback(async () => {
    if (!isAdmin) {
      setError("Access Denied: This page is for administrators only.");
      setLoading(false);
      setUsers([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const activeFilters: Partial<UserFilters> = {};
      for (const [key, value] of Object.entries(filters)) {
        if (value !== undefined && value !== "") (activeFilters as any)[key] = value;
      }
      const usersData = await listUsers(activeFilters);
      setUsers(usersData);
    } catch (err: any) {
      setUsers([]);
      setError(err?.error?.message || err?.message || "Failed to fetch users.");
    } finally {
      setLoading(false);
    }
  }, [filters, isAdmin]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleFilterChange = (key: keyof UserFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleBooleanFilterChange = (key: keyof UserFilters, value: string) => {
    if (value === "any") setFilters(prev => ({ ...prev, [key]: undefined }));
    else setFilters(prev => ({ ...prev, [key]: value === "true" }));
  };

  const handleResetFilters = () => {
    setFilters({ search: "", role: "", is_active: undefined });
  };

  const handleToggleUserStatus = async (userToToggle: UserRead) => {
    if (!isAdmin) { setError("Unauthorized action."); return; }
    const actionVerb = userToToggle.is_active ? "деактивировать" : "активировать";
    if (!window.confirm(`Вы уверены, что хотите ${actionVerb} пользователя ${userToToggle.username}?`)) return;
    try {
      if (userToToggle.is_active) {
        await updateUser(userToToggle.id, { is_active: false });
      } else {
        await updateUser(userToToggle.id, { is_active: true });
      }
      fetchUsers(); // Refresh list
    } catch (err: any) {
      setError(err?.error?.message || err?.message || `Failed to ${actionVerb} user.`);
    }
  };

  if (!isAdmin && !loading) {
    return (
      <div className="container mx-auto py-10 px-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Access Denied</AlertTitle>
          <AlertDescription>This page is for administrators only.</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
        <h1 className="text-3xl font-bold flex items-center gap-3 text-gray-800 dark:text-white">
          <Users2 className="w-8 h-8 text-cyan-500" /> Управление пользователями
        </h1>
        {isAdmin && (
          <Link href="/users/new" legacyBehavior>
            <Button asChild size="lg" className="bg-cyan-500 hover:bg-cyan-600 text-white">
              <a><PlusCircle className="w-6 h-6 mr-2" /> Добавить пользователя</a>
            </Button>
          </Link>
        )}
      </div>

      {isAdmin && (
        <div className="mb-8 p-4 md:p-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg border dark:border-gray-700">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-6 gap-y-4">
            <div>
              <Label htmlFor="search-users" className="dark:text-gray-300 text-sm">Поиск</Label>
              <Input
                id="search-users"
                type="text"
                placeholder="Username, email, name..."
                value={filters.search || ""}
                onChange={(e) => handleFilterChange("search", e.target.value)}
                className="mt-1 dark:bg-gray-700 dark:border-gray-600"
              />
            </div>
            <div>
              <Label htmlFor="role-users" className="dark:text-gray-300 text-sm">Роль</Label>
              <Input
                id="role-users"
                type="text"
                placeholder="Фильтр по роли"
                value={filters.role || ""}
                onChange={(e) => handleFilterChange("role", e.target.value)}
                className="mt-1 dark:bg-gray-700 dark:border-gray-600"
              />
            </div>
            <div>
              <Label htmlFor="is_active-users" className="dark:text-gray-300 text-sm">Статус</Label>
              <Select
                value={filters.is_active === undefined ? "any" : (filters.is_active ? "true" : "false")}
                onValueChange={(value) => handleBooleanFilterChange("is_active", value)}
              >
                <SelectTrigger id="is_active-users" className="mt-1 dark:bg-gray-700 dark:border-gray-600"><SelectValue /></SelectTrigger>
                <SelectContent className="dark:bg-gray-700 dark:text-white">
                  <SelectItem value="any">Любой</SelectItem>
                  <SelectItem value="true">Активен</SelectItem>
                  <SelectItem value="false">Неактивен</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end space-x-3 col-span-full sm:col-span-1 md:col-start-auto">
              <Button onClick={fetchUsers} className="bg-cyan-500 hover:bg-cyan-600 text-white w-full sm:w-auto">
                <Search className="w-4 h-4 mr-2" />Применить
              </Button>
              <Button onClick={handleResetFilters} variant="outline" className="dark:text-gray-300 dark:border-gray-600 hover:bg-gray-700 w-full sm:w-auto">
                <X className="w-4 h-4 mr-2" />Сбросить
              </Button>
            </div>
          </div>
        </div>
      )}
      {loading && (
        <div className="text-center py-10 dark:text-gray-400">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-cyan-500" />
          Загрузка пользователей...
        </div>
      )}

      {error && !loading && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Ошибка</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!loading && !error && users.length === 0 && isAdmin && (
        <div className="text-center py-16 text-gray-500 dark:text-gray-400">
          <Users2 className="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500" />
          <h2 className="text-xl font-semibold mb-2">Пользователей не найдено</h2>
          <p className="text-sm">
            {Object.values(filters).some(v => v !== undefined && v !== "")
              ? "Нет пользователей, соответствующих фильтрам."
              : "Добавьте первого пользователя!"}
          </p>
        </div>
      )}

      {!loading && !error && users.length > 0 && isAdmin && (
        <Card className="dark:bg-gray-800 shadow-lg">
          <CardHeader>
            <CardTitle className="dark:text-white">Список пользователей</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="dark:text-gray-300">Username</TableHead>
                  <TableHead className="dark:text-gray-300 hidden md:table-cell">Email</TableHead>
                  <TableHead className="dark:text-gray-300 hidden lg:table-cell">Full Name</TableHead>
                  <TableHead className="dark:text-gray-300">Роли</TableHead>
                  <TableHead className="dark:text-gray-300 hidden md:table-cell">Статус</TableHead>
                  <TableHead className="dark:text-gray-300 hidden lg:table-cell">Обновлен</TableHead>
                  <TableHead className="dark:text-gray-300 text-right">Действия</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id} className="dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <TableCell className="font-medium dark:text-white">
                      <Link href={`/users/${user.id}`} className="hover:text-cyan-400">{user.username}</Link>
                    </TableCell>
                    <TableCell className="dark:text-gray-400 hidden md:table-cell">{user.email}</TableCell>
                    <TableCell className="dark:text-gray-400 hidden lg:table-cell">{user.full_name || "—"}</TableCell>
                    <TableCell className="dark:text-gray-400">
                      {user.roles?.length
                        ? user.roles.map((role) => (
                            <Badge key={role} variant="outline" className="dark:border-gray-600 mr-1">{role}</Badge>
                          ))
                        : <Badge variant="outline" className="dark:border-gray-600">user</Badge>
                      }
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      <Badge
                        variant={user.is_active ? "default" : "destructive"}
                        className={user.is_active
                          ? "bg-green-500 hover:bg-green-600 dark:bg-green-600 dark:hover:bg-green-700"
                          : "bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700"}
                      >
                        {user.is_active ? "Активен" : "Неактивен"}
                      </Badge>
                    </TableCell>
                    <TableCell className="dark:text-gray-400 hidden lg:table-cell">
                      {formatDate(user.updated_at)}
                    </TableCell>
                    <TableCell className="text-right space-x-1">
                      <Button variant="ghost" size="icon" asChild className="dark:text-gray-400 hover:dark:text-cyan-400">
                        <Link href={`/users/${user.id}`}>
                          <Edit3 className="w-4 h-4" />
                        </Link>
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleToggleUserStatus(user)}
                        className={user.is_active
                          ? "dark:text-gray-400 hover:dark:text-red-400"
                          : "dark:text-gray-400 hover:dark:text-green-400"}
                      >
                        {user.is_active ? <XCircle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
