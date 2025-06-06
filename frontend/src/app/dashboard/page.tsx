
// src/app/dashboard/page.tsx
// src/app/dashboard/page.tsx
"use client";

import React from "react";
import { useAuth } from "@/app/lib/auth";
import { useQuery } from "@tanstack/react-query";
import { listProjects, listTasks } from "@/app/lib/api";
import ProjectCard from "@/components/ProjectCard";
import TaskCard from "@/components/TaskCard";
import type { ProjectShort, TaskShort } from "@/app/lib/types";

export default function DashboardPage() {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();

  // Получаем проекты (ProjectShort[])
  const {
    data: projects,
    isLoading: isProjectsLoading,
    error: projectsError,
  } = useQuery<ProjectShort[]>({
    queryKey: ["projects"],
    queryFn: () => listProjects(),
    enabled: isAuthenticated,
    refetchOnWindowFocus: false,
  });

  // Получаем задачи (TaskShort[])
  const {
    data: tasks,
    isLoading: isTasksLoading,
    error: tasksError,
  } = useQuery<TaskShort[]>({
    queryKey: ["tasks"],
    queryFn: () => listTasks(),
    enabled: isAuthenticated,
    refetchOnWindowFocus: false,
  });

  // Лоадеры
  if (isAuthLoading || isProjectsLoading || isTasksLoading) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen">
        <span className="text-xl text-gray-500">Loading dashboard...</span>
      </div>
    );
  }

  // Ошибки
  if (projectsError || tasksError) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen text-red-500">
        <div>
          Ошибка загрузки данных:{" "}
          {projectsError?.message || tasksError?.message}
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-5xl mx-auto px-2 py-8 flex flex-col gap-8">
      <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
      {/* Краткая статистика */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-zinc-900 p-4 rounded-xl shadow flex flex-col items-center">
          <span className="text-2xl font-bold text-blue-400">{projects?.length ?? 0}</span>
          <span className="text-xs text-zinc-400">Projects</span>
        </div>
        <div className="bg-zinc-900 p-4 rounded-xl shadow flex flex-col items-center">
          <span className="text-2xl font-bold text-green-400">{tasks?.length ?? 0}</span>
          <span className="text-xs text-zinc-400">Tasks</span>
        </div>
        <div className="bg-zinc-900 p-4 rounded-xl shadow flex flex-col items-center">
          <span className="text-2xl font-bold text-yellow-400">
            {projects?.filter((p) => (p as any).is_favorite).length ?? 0}
          </span>
          <span className="text-xs text-zinc-400">Favorites</span>
        </div>
      </div>
      {/* Список проектов */}
      <div>
        <h2 className="text-xl font-semibold mb-3">Your Projects</h2>
        <div className="flex flex-wrap gap-4">
          {projects?.length
            ? projects.map((p) => (
                <ProjectCard key={p.id} {...p} />
              ))
            : <span className="text-gray-400">No projects yet</span>}
        </div>
      </div>
      {/* Активные задачи */}
      <div>
        <h2 className="text-xl font-semibold mb-3">Active Tasks</h2>
        <div className="flex flex-col gap-3">
          {tasks?.length
            ? tasks.map((t) => (
                <TaskCard key={t.id} {...t} />
              ))
            : <span className="text-gray-400">No tasks yet</span>}
        </div>
      </div>
    </div>
  );
}
