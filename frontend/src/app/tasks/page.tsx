"use client";

import React, { useEffect, useState, useCallback } from "react";
import { getTasks, TaskRead, TaskFilters, restoreTask } from "../../lib/api"; // Updated imports
import TaskCard from "../../components/TaskCard";
import { PlusCircle, ClipboardList, Search, X } from "lucide-react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { toast } from "sonner"; // Import toast
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Loader2 as PageLoaderIcon, AlertCircle as AlertErrorIcon } from "lucide-react"; // Renamed to avoid conflict

// Task type is now TaskRead from api.ts

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TaskFilters>({
    search: "",
    status: "",
    priority: undefined,
    project_id: undefined,
    assignee_id: undefined,
    is_archived: false,
    deadline_after: "",
    deadline_before: "",
  });

  const fetchTasks = useCallback(() => {
    setLoading(true);
    setError(null);
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    const activeFilters: Partial<TaskFilters> = {};
    for (const key in filters) {
        if (filters[key as keyof TaskFilters] !== "" && filters[key as keyof TaskFilters] !== undefined) {
            (activeFilters as any)[key] = filters[key as keyof TaskFilters];
        } else if (typeof filters[key as keyof TaskFilters] === 'boolean') {
             (activeFilters as any)[key] = filters[key as keyof TaskFilters];
        }
    }

    getTasks(activeFilters, token ?? undefined)
      .then(setTasks)
      .catch((err) => {
        setTasks([]);
        const errorMessage = err.message || "Failed to fetch tasks.";
        setError(errorMessage);
        toast.error(`Failed to load tasks: ${errorMessage}`);
      })
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleFilterChange = (key: keyof TaskFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleNumericFilterChange = (key: keyof TaskFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value === "" ? undefined : Number(value) }));
  };


  const handleResetFilters = () => {
    setFilters({
      search: "", status: "", priority: undefined, project_id: undefined, assignee_id: undefined,
      is_archived: false, deadline_after: "", deadline_before: "",
    });
  };

  const handleRestoreTask = async (taskId: any) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) {
      toast.error("Authentication token not found. Please log in.");
      setError("Authentication token not found. Please log in.");
      return;
    }
    const toastId = toast.loading("Restoring task...");
    try {
      await restoreTask(taskId.toString(), token);
      toast.success("Task restored successfully!", { id: toastId });
      fetchTasks();
    } catch (err: any) {
      const errorMessage = err.message || "Failed to restore task.";
      setError(errorMessage);
      toast.error(`Failed to restore task: ${errorMessage}`, { id: toastId });
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
        <h1 className="text-3xl font-bold flex items-center gap-3 text-gray-800 dark:text-white">
          <ClipboardList className="w-8 h-8 text-blue-500" /> Tasks
        </h1>
        <Link href="/tasks/new" legacyBehavior>
          <Button asChild size="lg" className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg flex items-center gap-2 transition-colors duration-150 shadow-md hover:shadow-lg">
            <a><PlusCircle className="w-6 h-6" />Create New Task</a>
          </Button>
        </Link>
      </div>

      {/* Filters Section */}
      <div className="mb-8 p-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {/* Search Filter */}
          <div><Label htmlFor="search-filter-task" className="text-sm font-medium text-gray-700 dark:text-gray-300">Search</Label><div className="relative mt-1"><Input id="search-filter-task" type="text" placeholder="Task name or description..." value={filters.search || ""} onChange={(e) => handleFilterChange("search", e.target.value)} className="pl-10 dark:bg-gray-700 dark:border-gray-600 dark:text-white" /><Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" /></div></div>
          {/* Status Filter */}
          <div><Label htmlFor="status-filter-task" className="text-sm font-medium text-gray-700 dark:text-gray-300">Status</Label><Select value={filters.status || ""} onValueChange={(value) => handleFilterChange("status", value)}><SelectTrigger id="status-filter-task" className="mt-1 dark:bg-gray-700 dark:border-gray-600 dark:text-white"><SelectValue placeholder="Any Status" /></SelectTrigger><SelectContent className="dark:bg-gray-700 dark:text-white"><SelectItem value="">Any Status</SelectItem><SelectItem value="todo">To Do</SelectItem><SelectItem value="in_progress">In Progress</SelectItem><SelectItem value="done">Done</SelectItem><SelectItem value="backlog">Backlog</SelectItem><SelectItem value="cancelled">Cancelled</SelectItem></SelectContent></Select></div>
          {/* Priority Filter */}
          <div><Label htmlFor="priority-filter-task" className="text-sm font-medium text-gray-700 dark:text-gray-300">Priority</Label><Select value={filters.priority?.toString() || ""} onValueChange={(value) => handleFilterChange("priority", value ? parseInt(value) : undefined)}><SelectTrigger id="priority-filter-task" className="mt-1 dark:bg-gray-700 dark:border-gray-600 dark:text-white"><SelectValue placeholder="Any Priority" /></SelectTrigger><SelectContent className="dark:bg-gray-700 dark:text-white"><SelectItem value="">Any Priority</SelectItem>{[1, 2, 3, 4, 5].map(p => <SelectItem key={p} value={p.toString()}>{p}</SelectItem>)}</SelectContent></Select></div>
          {/* Project ID Filter */}
          <div><Label htmlFor="project-id-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">Project ID</Label><Input id="project-id-filter" type="number" placeholder="Enter Project ID" value={filters.project_id?.toString() || ""} onChange={(e) => handleNumericFilterChange("project_id", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600 dark:text-white"/></div>
          {/* Assignee ID Filter */}
          <div><Label htmlFor="assignee-id-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">Assignee ID</Label><Input id="assignee-id-filter" type="number" placeholder="Enter Assignee ID" value={filters.assignee_id?.toString() || ""} onChange={(e) => handleNumericFilterChange("assignee_id", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600 dark:text-white"/></div>
          {/* Archived Filter */}
          <div className="flex items-center space-x-2 mt-2 md:mt-0 md:pt-6"><Checkbox id="archived-filter-task" checked={filters.is_archived || false} onCheckedChange={(checked) => handleFilterChange("is_archived", Boolean(checked))} className="dark:border-gray-600 data-[state=checked]:bg-blue-500"/><Label htmlFor="archived-filter-task" className="text-sm font-medium text-gray-700 dark:text-gray-300">Show Archived</Label></div>
          {/* Action Buttons */}
          <div className="flex items-end space-x-3 col-span-full sm:col-span-1 md:col-start-auto"><Button onClick={fetchTasks} className="bg-blue-500 hover:bg-blue-600 text-white w-full sm:w-auto"><Search className="w-4 h-4 mr-2" /> Apply Filters</Button><Button onClick={handleResetFilters} variant="outline" className="text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 w-full sm:w-auto"><X className="w-4 h-4 mr-2" /> Reset</Button></div>
        </div>
      </div>

      {loading &&
        <div className="flex flex-col items-center justify-center text-center text-gray-500 dark:text-gray-400 py-20">
          <PageLoaderIcon className="w-12 h-12 animate-spin text-blue-500 mb-4" />
          <p className="text-lg">Loading tasks...</p>
        </div>
      }
      {error && !loading && (
        <Alert variant="destructive" className="mb-6">
          <AlertErrorIcon className="h-5 w-5" />
          <AlertTitle className="font-semibold">Error Fetching Tasks</AlertTitle>
          <AlertDescription>
            {error} <br/>Please try again.
            <Button variant="outline" size="sm" onClick={fetchTasks} className="mt-3 ml-auto block">Retry</Button>
          </AlertDescription>
        </Alert>
      )}
      {!loading && !error && tasks.length === 0 && (
        <div className="text-center text-gray-500 dark:text-gray-400 py-16 border-2 border-dashed dark:border-gray-700 rounded-xl">
          <ClipboardList className="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500"/>
          <h2 className="text-2xl font-semibold mb-2">No Tasks Found</h2>
          <p className="text-md mb-4">
            {Object.values(filters).some(v => v && v !== false && (typeof v !== 'object' || Object.keys(v).length > 0))
              ? "No tasks match your current filters. Try adjusting them."
              : "You haven't created any tasks yet!"}
          </p>
          <Link href="/tasks/new" legacyBehavior>
            <Button className="bg-blue-500 hover:bg-blue-600 text-white text-lg px-6 py-3">
              <PlusCircle className="w-5 h-5 mr-2" /> Create Your First Task
            </Button>
          </Link>
        </div>
      )}
      {!loading && !error && tasks.length > 0 && (
        <div className="space-y-4">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task} // Pass the whole task object
              onRestore={filters.is_archived ? handleRestoreTask : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
