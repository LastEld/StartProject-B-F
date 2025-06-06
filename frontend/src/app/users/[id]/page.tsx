"use client";

import React, { useEffect, useState, ChangeEvent, FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { getUser, updateUser, deleteUser } from "@/app/lib/api";
import type { UserRead, UserUpdate } from "@/app/lib/types";
import { useAuth } from "@/app/lib/useAuth";
import {
  Card, CardHeader, CardContent, CardTitle, CardDescription, CardFooter
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";

export default function UserProfilePage() {
  const { id } = useParams<{ id: string }>();
  const userId = Number(id);
  const router = useRouter();
  const { user: currentUser } = useAuth();

  const [user, setUser] = useState<UserRead | null>(null);
  const [editData, setEditData] = useState<UserUpdate>({});
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getUser(userId)
      .then((u) => {
        setUser(u);
        setEditData({
          email: u.email,
          full_name: u.full_name,
          is_active: u.is_active,
          is_superuser: u.is_superuser,
          roles: u.roles,
        });
        setLoading(false);
      })
      .catch((e) => {
        setError(typeof e === "object" && e?.error?.message ? e.error.message : "Не удалось загрузить пользователя");
        setLoading(false);
      });
  }, [userId]);

  // Чисто типизированный обработчик для input/select (без чекбоксов!)
  const handleInputChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    if (name === "roles") {
      setEditData((prev) => ({
        ...prev,
        roles: value.split(",").map((r) => r.trim()),
      }));
    } else {
      setEditData((prev) => ({
        ...prev,
        [name]: value,
      }));
    }
  };

  // Для чекбоксов
  const handleCheckboxChange = (name: keyof UserUpdate, checked: boolean) => {
    setEditData((prev) => ({
      ...prev,
      [name]: checked,
    }));
  };

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateUser(userId, editData);
      setUser(updated);
      setIsEditing(false);
      setSuccess("Профиль обновлен");
    } catch (e: any) {
      setError(typeof e === "object" && e?.error?.message ? e.error.message : "Ошибка при сохранении");
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async () => {
    if (!confirm("Вы уверены, что хотите деактивировать пользователя?")) return;
    setSaving(true);
    setError(null);
    try {
      await deleteUser(userId);
      setSuccess("Пользователь деактивирован");
      router.push("/users");
    } catch (e: any) {
      setError(typeof e === "object" && e?.error?.message ? e.error.message : "Ошибка при деактивации");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card className="max-w-xl mx-auto mt-8">
        <CardHeader>
          <Skeleton className="h-8 w-40 mb-2" />
          <Skeleton className="h-4 w-20" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-6 w-full mb-2" />
          <Skeleton className="h-6 w-1/2" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="max-w-xl mx-auto mt-8">
        <AlertTitle>Ошибка</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!user) return null;

  return (
    <Card className="max-w-xl mx-auto mt-8">
      <CardHeader>
        <CardTitle>
          {user.full_name || user.username}
          {user.is_superuser && <Badge className="ml-2">Superuser</Badge>}
        </CardTitle>
        <CardDescription>ID: {user.id}</CardDescription>
      </CardHeader>
      <CardContent>
        {success && (
          <Alert variant ="default" className="mb-4">
            <AlertTitle>Успех</AlertTitle>
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}
        {isEditing ? (
          <form onSubmit={handleSave} className="flex flex-col gap-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                value={editData.email ?? ""}
                onChange={handleInputChange}
                required
              />
            </div>
            <div>
              <Label htmlFor="full_name">Имя</Label>
              <Input
                id="full_name"
                name="full_name"
                value={editData.full_name ?? ""}
                onChange={handleInputChange}
                placeholder="ФИО"
              />
            </div>
            <div>
              <Label htmlFor="roles">Роли (через запятую)</Label>
              <Input
                id="roles"
                name="roles"
                value={editData.roles?.join(", ") ?? ""}
                onChange={handleInputChange}
              />
            </div>
            <div className="flex gap-4 items-center">
              <Checkbox
                id="is_active"
                checked={!!editData.is_active}
                onCheckedChange={(checked) =>
                  handleCheckboxChange("is_active", !!checked)
                }
              />
              <Label htmlFor="is_active">Активен</Label>
              <Checkbox
                id="is_superuser"
                checked={!!editData.is_superuser}
                onCheckedChange={(checked) =>
                  handleCheckboxChange("is_superuser", !!checked)
                }
              />
              <Label htmlFor="is_superuser">Суперпользователь</Label>
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={saving}>
                {saving ? "Сохраняем..." : "Сохранить"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsEditing(false)}
                disabled={saving}
              >
                Отмена
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-3">
            <div>
              <Label>Email:</Label> {user.email}
            </div>
            <div>
              <Label>Имя:</Label> {user.full_name}
            </div>
            <div>
              <Label>Роли:</Label>{" "}
              {user.roles.length > 0
                ? user.roles.map((role) => <Badge key={role}>{role}</Badge>)
                : "—"}
            </div>
            <div>
              <Label>Активен:</Label>{" "}
              <Badge color={user.is_active ? "green" : "red"}>
                {user.is_active ? "Да" : "Нет"}
              </Badge>
            </div>
            <div>
              <Label>Суперпользователь:</Label>{" "}
              <Badge color={user.is_superuser ? "blue" : "gray"}>
                {user.is_superuser ? "Да" : "Нет"}
              </Badge>
            </div>
            <div>
              <Label>Создан:</Label> {new Date(user.created_at).toLocaleString()}
            </div>
            <div>
              <Label>Обновлен:</Label> {new Date(user.updated_at).toLocaleString()}
            </div>
            <div className="flex gap-2 mt-4">
              {(currentUser?.is_superuser || currentUser?.id === user.id) && (
                <Button onClick={() => setIsEditing(true)}>Редактировать</Button>
              )}
              {(currentUser?.is_superuser && user.is_active) && (
                <Button
                  type="button"
                  variant="destructive"
                  onClick={handleDeactivate}
                  disabled={saving}
                >
                  {saving ? "Деактивация..." : "Деактивировать"}
                </Button>
              )}
            </div>
          </div>
        )}
      </CardContent>
      <CardFooter>
        {/* Здесь можно добавить дополнительные действия */}
      </CardFooter>
    </Card>
  );
}
