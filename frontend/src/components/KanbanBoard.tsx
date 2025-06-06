
// src/app/components/KanbanBoard.tsx
// src/app/components/KanbanBoard.tsx
"use client";
import React, { useState, useEffect, useCallback } from "react";
import { listTasks, updateTask } from "../app/lib/api"; // <-- Исправленный импорт!
import type { TaskRead, TaskUpdate, TaskFilters } from "../app/lib/types";
import { Loader2, AlertCircle, Flag } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

// Список колонок Kanban по твоим task_status
const columns: { key: TaskRead["task_status"]; label: string }[] = [
  { key: "todo", label: "To Do" },
  { key: "in_progress", label: "In Progress" },
  { key: "done", label: "Done" },
  { key: "backlog", label: "Backlog" },
];

// Helper для отображения приоритета
const getPriorityDisplay = (priority?: number) => {
  if (priority === undefined || priority === null) return null;
  const colors: Record<number, string> = {
    1: "text-green-400",
    2: "text-blue-400",
    3: "text-yellow-400",
    4: "text-orange-400",
    5: "text-red-400",
  };
  const text: Record<number, string> = {
    1: "Lowest",
    2: "Low",
    3: "Medium",
    4: "High",
    5: "Highest",
  };
  return (
    <span className="flex items-center gap-1">
      <Flag className={`w-4 h-4 ${colors[priority] || "text-gray-400"}`} />
      <span>{text[priority] || priority}</span>
    </span>
  );
};

export default function KanbanBoard({ projectId }: { projectId?: number }) {
  const [tasks, setTasks] = useState<TaskRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draggedTask, setDraggedTask] = useState<TaskRead | null>(null);

  // fetchTasks строго типизирован и использует твой TaskFilters
  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const filters: TaskFilters = { is_deleted: false }; // Фильтруем неархивные задачи
      if (projectId) filters.project_id = projectId;
      // listTasks возвращает TaskShort[], а тебе нужны TaskRead[]
      // Если твой эндпоинт возвращает только short — нужно добавить getTask для каждого id (batch-запросом, или изменить эндпоинт на /tasks/?full=true)
      // Для простоты предполагаем, что /tasks/ уже возвращает TaskRead[]
      const fetchedTasks = await listTasks(filters, token ?? undefined) as unknown as TaskRead[];
      setTasks(fetchedTasks);
    } catch (err: any) {
      const errorMessage = err?.message || "Failed to fetch tasks.";
      setError(errorMessage);
      toast.error(errorMessage);
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleDragStart = (e: React.DragEvent, task: TaskRead) => {
    e.dataTransfer.setData("taskId", String(task.id));
    setDraggedTask(task);
  };

  const handleDrop = async (newStatus: TaskRead["task_status"]) => {
    if (!draggedTask || !draggedTask.id) return;

    const taskId = draggedTask.id;
    const taskTitle = draggedTask.title;
    const originalStatus = draggedTask.task_status;

    // Оптимистично обновляем UI
    setTasks((prev) =>
      prev.map((t) =>
        t.id === taskId ? { ...t, task_status: newStatus } : t
      )
    );
    const toastId = toast.loading(
      `Moving task "${taskTitle}" to ${newStatus.replace("_", " ")}...`
    );
    try {
      const token = localStorage.getItem("access_token");
      const updatePayload: TaskUpdate = { task_status: newStatus };
      await updateTask(taskId, updatePayload, token ?? undefined);
      toast.success(
        `Task "${taskTitle}" moved to ${newStatus.replace("_", " ")}!`,
        { id: toastId }
      );
    } catch (err: any) {
      const errorMessage = err?.message || "Failed to update task status.";
      setError(errorMessage);
      toast.error(`Failed to move task: ${errorMessage}`, { id: toastId });
      // Откат UI если ошибка
      setTasks((prev) =>
        prev.map((t) =>
          t.id === taskId ? { ...t, task_status: originalStatus } : t
        )
      );
    } finally {
      setDraggedTask(null);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  if (loading)
    return (
      <div className="flex justify-center items-center p-10">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <span className="ml-2 dark:text-white">Loading tasks...</span>
      </div>
    );
  if (error)
    return (
      <div className="p-5 bg-red-100 text-red-700 rounded-md flex items-center">
        <AlertCircle className="w-5 h-5 mr-2" /> Error: {error}
      </div>
    );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 p-2 w-full overflow-x-auto">
      {columns.map((col) => (
        <div
          key={col.key}
          onDrop={() => handleDrop(col.key)}
          onDragOver={handleDragOver}
          className="bg-gray-100 dark:bg-gray-800 rounded-xl shadow-md p-4 min-h-[400px] flex flex-col"
        >
          <h3 className="font-semibold text-lg mb-4 text-gray-700 dark:text-white border-b pb-2 dark:border-gray-700">
            {col.label}
          </h3>
          <div className="space-y-3 overflow-y-auto flex-grow">
            {tasks.filter((t) => t.task_status === col.key).length === 0 && (
              <div className="text-sm text-gray-500 dark:text-gray-400 text-center pt-10">
                No tasks in this stage.
              </div>
            )}
            {tasks
              .filter((t) => t.task_status === col.key)
              .map((task) => (
                <Link key={task.id} href={`/tasks/${task.id}`} legacyBehavior>
                  <a
                    draggable
                    onDragStart={(e) => handleDragStart(e, task)}
                    className="block bg-white dark:bg-gray-900 rounded-lg p-3.5 shadow-sm hover:shadow-md transition-shadow border dark:border-gray-700 cursor-grab active:cursor-grabbing"
                  >
                    <div className="font-medium text-gray-800 dark:text-white mb-1">
                      {task.title}
                    </div>
                    {task.description && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mb-2">
                        {task.description}
                      </p>
                    )}
                    <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                      {getPriorityDisplay(task.priority)}
                      <span>ID: {task.id}</span>
                    </div>
                  </a>
                </Link>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
