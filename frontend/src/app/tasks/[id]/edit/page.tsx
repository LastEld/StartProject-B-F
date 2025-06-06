"use client";

import React, { useState, useEffect, ChangeEvent, FormEvent } from "react";
import { useRouter, useParams } from "next/navigation";
import { getTask, updateTask } from "../../../../lib/api";
import { Input } from "../../../../components/ui/input";
import { Button } from "../../../../components/ui/button";
import { AlertCircle, Loader2 } from "lucide-react";

// Type for form data (can be similar to NewTaskData or Task type)
interface EditTaskData {
  name: string;
  description: string; // Changed to string for controlled component, can be empty
  projectId: string; // Assuming string, can be empty
  status: "todo" | "in_progress" | "done";
  priority: "low" | "medium" | "high";
}

const statusOptions: EditTaskData["status"][] = ["todo", "in_progress", "done"];
const priorityOptions: EditTaskData["priority"][] = ["low", "medium", "high"];

export default function EditTaskPage() {
  const router = useRouter();
  const params = useParams();
  const id = params?.id as string | undefined; // id can be string or undefined

  const [formData, setFormData] = useState<EditTaskData>({
    name: "",
    description: "",
    projectId: "",
    status: "todo",
    priority: "medium",
  });

  const [isFetching, setIsFetching] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setIsFetching(false);
      setFetchError("Task ID is missing.");
      return;
    }

    setIsFetching(true);
    setFetchError(null);
    getTask(Number(id))
      .then((task) => {
        if (task) {
          setFormData({
            name: task.name || "",
            description: task.description || "",
            projectId: task.projectId?.toString() || "", // Ensure string
            status: task.status || "todo",
            priority: task.priority || "medium",
          });
        } else {
          setFetchError("Task not found.");
        }
      })
      .catch((err) => {
        console.error("Failed to fetch task:", err);
        setFetchError(err.message || "Failed to load task details.");
      })
      .finally(() => {
        setIsFetching(false);
      });
  }, [id]);

  const handleChange = (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!id) {
      setUpdateError("Task ID is missing, cannot update.");
      return;
    }
    if (!formData.name.trim()) {
      setUpdateError("Task name is required.");
      return;
    }

    setIsUpdating(true);
    setUpdateError(null);

    try {
      // Ensure all fields are correctly typed if API is strict
      const dataToUpdate: Partial<EditTaskData> = {
        ...formData,
        projectId: formData.projectId || undefined, // Send undefined if empty, or handle as needed
        description: formData.description || undefined,
      };
      await updateTask(id, dataToUpdate); // Pass token if required
      router.push(`/tasks/${id}`); // Navigate to the detail page of the updated task
    } catch (err: any) {
      console.error("Failed to update task:", err);
      setUpdateError(err.message || "An unknown error occurred. Please try again.");
      setIsUpdating(false);
    }
  };

  if (isFetching) {
    return (
      <div className="max-w-2xl mx-auto py-10 px-4 text-center text-zinc-400">
        <Loader2 className="mr-2 h-8 w-8 animate-spin inline-block" /> Loading task details...
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="max-w-2xl mx-auto py-10 px-4 text-center bg-red-900/30 text-red-400 border border-red-700 rounded-md">
        <AlertCircle className="w-8 h-8 mx-auto mb-2" />
        <p>{fetchError}</p>
        <Button onClick={() => router.push('/tasks')} className="mt-4">Back to Tasks</Button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-white mb-8">Edit Task</h1>

      {updateError && (
        <div className="mb-6 p-4 bg-red-900/30 text-red-400 border border-red-700 rounded-md flex items-center">
          <AlertCircle className="w-5 h-5 mr-3 flex-shrink-0" />
          <p>{updateError}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6 bg-zinc-900 p-8 rounded-lg shadow-xl">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-zinc-300 mb-1">
            Task Name <span className="text-red-500">*</span>
          </label>
          <Input
            id="name"
            name="name"
            type="text"
            value={formData.name}
            onChange={handleChange}
            required
            className="bg-zinc-800 border-zinc-700 text-white focus:ring-blue-500 focus:border-blue-500"
            disabled={isUpdating}
          />
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-zinc-300 mb-1">
            Description
          </label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={4}
            className="w-full p-2 bg-zinc-800 border border-zinc-700 text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            disabled={isUpdating}
          />
        </div>

        <div>
          <label htmlFor="projectId" className="block text-sm font-medium text-zinc-300 mb-1">
            Project ID (Optional)
          </label>
          <Input
            id="projectId"
            name="projectId"
            type="text"
            value={formData.projectId}
            onChange={handleChange}
            className="bg-zinc-800 border-zinc-700 text-white focus:ring-blue-500 focus:border-blue-500"
            disabled={isUpdating}
          />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label htmlFor="status" className="block text-sm font-medium text-zinc-300 mb-1">
              Status
            </label>
            <select
              id="status"
              name="status"
              value={formData.status}
              onChange={handleChange}
              className="w-full p-2.5 bg-zinc-800 border border-zinc-700 text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              disabled={isUpdating}
            >
              {statusOptions.map(option => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1).replace("_", " ")}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="priority" className="block text-sm font-medium text-zinc-300 mb-1">
              Priority
            </label>
            <select
              id="priority"
              name="priority"
              value={formData.priority}
              onChange={handleChange}
              className="w-full p-2.5 bg-zinc-800 border border-zinc-700 text-white rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              disabled={isUpdating}
            >
              {priorityOptions.map(option => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <Button
            type="submit"
            className="w-full bg-green-600 hover:bg-green-700 text-white flex items-center justify-center"
            disabled={isUpdating || isFetching}
          >
            {(isUpdating) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isUpdating ? "Updating Task..." : "Update Task"}
          </Button>
        </div>
      </form>
    </div>
  );
}
