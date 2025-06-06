"use client";

import React, { useState, ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createProject, ProjectCreate } from "../../../lib/api"; // Adjusted path, imported ProjectCreate
import { Input } from "../../../components/ui/input";
import { Button } from "../../../components/ui/button";
import { Textarea } from "../../../components/ui/textarea"; // Assuming Textarea component exists
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../../components/ui/select"; // Assuming Select component
import { Label } from "../../../components/ui/label";
import { AlertCircle, Loader2, CalendarIcon } from "lucide-react";
import { toast } from "sonner"; // Import toast

// Type for form data is now ProjectCreate from api.ts
const initialFormData: ProjectCreate = {
  name: "",
  description: "",
  status: "not_started",
  priority: 3,
  tags: [],
  deadline: null,
};

export default function CreateProjectPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<ProjectCreate>(initialFormData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null); // For inline error display if needed

  const handleChange = (
    e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSelectChange = (name: keyof ProjectCreate, value: string | number) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleTagsChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { value } = e.target;
    setFormData(prev => ({ ...prev, tags: value.split(',').map(tag => tag.trim()).filter(tag => tag) }));
  };


  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError("Project name is required."); // Can also use toast here
      toast.error("Project name is required.");
      return;
    }
    setIsLoading(true);
    setError(null);
    const toastId = toast.loading("Creating project...");

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const dataToSubmit = {
        ...formData,
        deadline: formData.deadline ? new Date(formData.deadline).toISOString() : null,
        priority: formData.priority ? Number(formData.priority) : null,
      };
      const newProject = await createProject(dataToSubmit, token ?? undefined);
      
      toast.success(`Project "${newProject.name}" created successfully!`, { id: toastId });

      if (newProject && newProject.id) {
        router.push(`/projects/${newProject.id}`);
      } else {
        console.warn("Project created, but no ID received. Redirecting to projects list.");
        router.push("/projects");
      }
    } catch (err: any) {
      console.error("Failed to create project:", err);
      const errorMessage = err.message || "An unknown error occurred. Please try again.";
      setError(errorMessage); // Keep for inline error if desired
      toast.error(`Failed to create project: ${errorMessage}`, { id: toastId });
    } finally {
      // setIsLoading(false) is not set here because of redirect.
      // If creation fails and user stays on page, then set it.
      // However, toast.loading is dismissed by success/error toast with same ID.
      // If redirect doesn't happen on error, then:
      if (error) setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-3xl py-12 px-4">
      <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-10 text-center">
        Launch a New Project
      </h1>

      {error && (
        <div className="mb-6 p-4 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-lg flex items-center shadow">
          <AlertCircle className="w-6 h-6 mr-3 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8 bg-white dark:bg-gray-800 p-8 md:p-10 rounded-xl shadow-2xl border dark:border-gray-700">
        {/* Project Name */}
        <div>
          <Label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Project Name <span className="text-red-500">*</span>
          </Label>
          <Input
            id="name"
            name="name"
            type="text"
            value={formData.name}
            onChange={handleChange}
            placeholder="e.g., Website Redesign, Q4 Marketing Campaign"
            required
            className="dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            disabled={isLoading}
          />
        </div>

        {/* Description */}
        <div>
          <Label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description
          </Label>
          <Textarea
            id="description"
            name="description"
            value={formData.description || ""}
            onChange={handleChange}
            rows={5}
            placeholder="Provide a brief overview of the project, its goals, and scope."
            className="dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            disabled={isLoading}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Status */}
          <div>
            <Label htmlFor="status" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Status
            </Label>
            <Select
              name="status"
              value={formData.status || "not_started"}
              onValueChange={(value) => handleSelectChange("status", value)}
              disabled={isLoading}
            >
              <SelectTrigger className="dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent className="dark:bg-gray-700 dark:text-white">
                <SelectItem value="not_started">Not Started</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="on_hold">On Hold</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Priority */}
          <div>
            <Label htmlFor="priority" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Priority
            </Label>
            <Select
              name="priority"
              value={formData.priority?.toString() || "3"}
              onValueChange={(value) => handleSelectChange("priority", parseInt(value))}
              disabled={isLoading}
            >
              <SelectTrigger className="dark:bg-gray-700 dark:border-gray-600 dark:text-white">
                <SelectValue placeholder="Select priority" />
              </SelectTrigger>
              <SelectContent className="dark:bg-gray-700 dark:text-white">
                <SelectItem value="1">Lowest</SelectItem>
                <SelectItem value="2">Low</SelectItem>
                <SelectItem value="3">Medium</SelectItem>
                <SelectItem value="4">High</SelectItem>
                <SelectItem value="5">Highest</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Deadline */}
        <div>
          <Label htmlFor="deadline" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Deadline
          </Label>
          <div className="relative">
            <Input
              id="deadline"
              name="deadline"
              type="date"
              value={formData.deadline ? (formData.deadline instanceof Date ? formData.deadline.toISOString().split('T')[0] : formData.deadline.toString().split('T')[0]) : ""}
              onChange={handleChange}
              className="dark:bg-gray-700 dark:border-gray-600 dark:text-white pr-10"
              disabled={isLoading}
            />
            <CalendarIcon className="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          </div>
        </div>

        {/* Tags */}
        <div>
          <Label htmlFor="tags" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Tags <span className="text-xs text-gray-500 dark:text-gray-400">(comma-separated)</span>
          </Label>
          <Input
            id="tags"
            name="tags"
            type="text"
            value={Array.isArray(formData.tags) ? formData.tags.join(', ') : ""}
            onChange={handleTagsChange}
            placeholder="e.g., marketing, tech, Q1"
            className="dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            disabled={isLoading}
          />
        </div>


        <div className="pt-4">
          <Button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white font-semibold py-3 text-lg rounded-md shadow-md hover:shadow-lg transition-all duration-150 ease-in-out flex items-center justify-center"
            disabled={isLoading}
          >
            {isLoading && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
            {isLoading ? "Launching Project..." : "Launch Project"}
          </Button>
        </div>
      </form>
    </div>
  );
}
