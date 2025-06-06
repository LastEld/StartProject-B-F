"use client";

import React, { useState, ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createTask, TaskCreate } from "../../../lib/api"; // Updated imports
import { Input } from "../../../components/ui/input";
import { Button } from "../../../components/ui/button";
import { Textarea } from "../../../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select";
import { Label } from "../../../components/ui/label";
import { AlertCircle, Loader2, CalendarIcon } from "lucide-react";
import { toast } from "sonner"; // Import toast

const initialFormData: TaskCreate = {
  name: "",
  description: "",
  project_id: undefined,
  assignee_id: undefined,
  status: "todo",
  priority: 3,
  deadline: null,
  tags: [],
};

export default function CreateTaskPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<TaskCreate>(initialFormData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null); // For potential inline field errors

  const handleChange = (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
     if (type === 'number') {
      setFormData((prev) => ({ ...prev, [name]: value === '' ? undefined : Number(value) }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  const handleSelectChange = (name: keyof TaskCreate, value: string | number) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleTagsChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { value } = e.target;
    setFormData(prev => ({ ...prev, tags: value.split(',').map(tag => tag.trim()).filter(tag => tag) }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError("Task name is required."); // Keep for inline error if needed
      toast.error("Task name is required.");
      return;
    }
    setIsLoading(true);
    setError(null);
    const toastId = toast.loading("Creating task...");

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const dataToSubmit: TaskCreate = {
        ...formData,
        project_id: formData.project_id ? Number(formData.project_id) : undefined,
        assignee_id: formData.assignee_id ? Number(formData.assignee_id) : undefined,
        priority: formData.priority ? Number(formData.priority) : undefined,
        deadline: formData.deadline ? new Date(formData.deadline).toISOString() : null,
      };

      const newTask = await createTask(dataToSubmit, token ?? undefined);
      toast.success(`Task "${newTask.name}" created successfully!`, { id: toastId });

      if (newTask && newTask.id) {
        router.push(`/tasks/${newTask.id}`);
      } else {
        router.push("/tasks");
      }
    } catch (err: any) {
      console.error("Failed to create task:", err);
      const errorMessage = err.message || "An unknown error occurred. Please try again.";
      setError(errorMessage); // For inline error display
      toast.error(`Failed to create task: ${errorMessage}`, { id: toastId });
      setIsLoading(false); // Re-enable form only on error
    }
    // On success, redirection occurs, so no setIsLoading(false) here.
  };

  return (
    <div className="container mx-auto max-w-2xl py-12 px-4">
      <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-10 text-center">Add New Task</h1>

      {error && (
        <div className="mb-6 p-4 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-lg flex items-center shadow">
          <AlertCircle className="w-5 h-5 mr-3 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 p-8 rounded-xl shadow-xl border dark:border-gray-700">
        {/* Task Name */}
        <div>
          <Label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Task Name <span className="text-red-500">*</span></Label>
          <Input id="name" name="name" type="text" value={formData.name} onChange={handleChange} placeholder="e.g., Design homepage mockups" required className="dark:bg-gray-700 dark:border-gray-600 dark:text-white" disabled={isLoading} />
        </div>

        {/* Description */}
        <div>
          <Label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</Label>
          <Textarea id="description" name="description" value={formData.description || ""} onChange={handleChange} rows={4} placeholder="Add more details about the task..." className="dark:bg-gray-700 dark:border-gray-600 dark:text-white" disabled={isLoading} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Project ID */}
          <div>
            <Label htmlFor="project_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Project ID</Label>
            <Input id="project_id" name="project_id" type="number" value={formData.project_id || ""} onChange={handleChange} placeholder="Optional project ID" className="dark:bg-gray-700 dark:border-gray-600 dark:text-white" disabled={isLoading} />
          </div>
          {/* Assignee ID */}
          <div>
            <Label htmlFor="assignee_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Assignee ID</Label>
            <Input id="assignee_id" name="assignee_id" type="number" value={formData.assignee_id || ""} onChange={handleChange} placeholder="Optional assignee ID" className="dark:bg-gray-700 dark:border-gray-600 dark:text-white" disabled={isLoading} />
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Status */}
          <div>
            <Label htmlFor="status" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status</Label>
            <Select name="status" value={formData.status || "todo"} onValueChange={(value) => handleSelectChange("status", value)} disabled={isLoading}>
              <SelectTrigger className="dark:bg-gray-700 dark:border-gray-600 dark:text-white"><SelectValue /></SelectTrigger>
              <SelectContent className="dark:bg-gray-700 dark:text-white">
                <SelectItem value="todo">To Do</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="done">Done</SelectItem>
                <SelectItem value="backlog">Backlog</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {/* Priority */}
          <div>
            <Label htmlFor="priority" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Priority</Label>
            <Select name="priority" value={formData.priority?.toString() || "3"} onValueChange={(value) => handleSelectChange("priority", parseInt(value))} disabled={isLoading}>
              <SelectTrigger className="dark:bg-gray-700 dark:border-gray-600 dark:text-white"><SelectValue /></SelectTrigger>
              <SelectContent className="dark:bg-gray-700 dark:text-white">
                <SelectItem value="1">Lowest</SelectItem><SelectItem value="2">Low</SelectItem><SelectItem value="3">Medium</SelectItem><SelectItem value="4">High</SelectItem><SelectItem value="5">Highest</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Deadline */}
        <div>
          <Label htmlFor="deadline" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Deadline</Label>
          <div className="relative">
            <Input id="deadline" name="deadline" type="date" value={formData.deadline ? formData.deadline.toString().split('T')[0] : ""} onChange={handleChange} className="dark:bg-gray-700 dark:border-gray-600 dark:text-white pr-10" disabled={isLoading} />
            <CalendarIcon className="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          </div>
        </div>

        {/* Tags */}
        <div>
          <Label htmlFor="tags" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tags <span className="text-xs text-gray-500 dark:text-gray-400">(comma-separated)</span></Label>
          <Input id="tags" name="tags" type="text" value={Array.isArray(formData.tags) ? formData.tags.join(', ') : ""} onChange={handleTagsChange} placeholder="e.g., frontend, bug, high-effort" className="dark:bg-gray-700 dark:border-gray-600 dark:text-white" disabled={isLoading} />
        </div>

        <div className="pt-4">
          <Button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white font-semibold py-3 text-lg rounded-md shadow-md hover:shadow-lg" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
            {isLoading ? "Adding Task..." : "Add Task"}
          </Button>
        </div>
      </form>
    </div>
  );
}
