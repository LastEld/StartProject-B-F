"use client";

import React, { useState, ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createDevlogEntry, DevLogCreate } from "../../../lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { AlertCircle, Loader2, BookText } from "lucide-react";
import { toast } from "sonner"; // Import toast

const entryTypes = ["general", "meeting", "code", "research", "decision", "debug", "release", "issue"];

const initialFormData: DevLogCreate = {
  title: "",
  content: "",
  entry_type: "general",
  project_id: undefined,
  task_id: undefined,
  tags: [],
};

export default function CreateDevLogEntryPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<DevLogCreate>(initialFormData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null); // For inline field errors

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    const isNumericField = type === 'number' || name === 'project_id' || name === 'task_id';
    setFormData(prev => ({ ...prev, [name]: isNumericField && value === '' ? undefined : (isNumericField ? Number(value) : value) }));
  };

  const handleSelectChange = (name: keyof DevLogCreate, value: string) => {
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleTagsChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { value } = e.target;
    setFormData(prev => ({ ...prev, tags: value.split(',').map(tag => tag.trim()).filter(tag => tag) }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      setError("Title is required."); toast.error("Title is required."); return;
    }
    if (!formData.content.trim()) {
      setError("Content is required."); toast.error("Content is required."); return;
    }
    setIsLoading(true); setError(null);
    const toastId = toast.loading("Creating DevLog entry...");

    try {
      const token = localStorage.getItem("access_token");
      const dataToSubmit: DevLogCreate = {
        ...formData,
        project_id: formData.project_id ? Number(formData.project_id) : undefined,
        task_id: formData.task_id ? Number(formData.task_id) : undefined,
      };

      const newEntry = await createDevlogEntry(dataToSubmit, token ?? undefined);
      toast.success(`DevLog entry "${newEntry.title}" created!`, { id: toastId });

      if (newEntry && newEntry.id) {
        router.push(`/devlog/${newEntry.id}`);
      } else {
        router.push("/devlog");
      }
    } catch (err: any) {
      const errorMessage = err.message || "An unknown error occurred.";
      setError(errorMessage); // Keep for potential inline display
      toast.error(`Failed to create entry: ${errorMessage}`, { id: toastId });
      setIsLoading(false); // Re-enable form on error
    }
    // On success, redirection occurs, setIsLoading not needed here in that path.
  };

  return (
    <div className="container mx-auto max-w-2xl py-12 px-4">
      <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-10 text-center flex items-center justify-center">
        <BookText className="w-8 h-8 mr-3 text-purple-500" /> Create New DevLog Entry
      </h1>

      {error && (
        <div className="mb-6 p-4 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-lg flex items-center shadow">
          <AlertCircle className="w-5 h-5 mr-3" /> <p className="text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 p-8 rounded-xl shadow-xl border dark:border-gray-700">
        <div>
          <Label htmlFor="title" className="mb-1 block dark:text-gray-300">Title <span className="text-red-500">*</span></Label>
          <Input id="title" name="title" type="text" value={formData.title} onChange={handleChange} placeholder="Brief title for your entry" required className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} />
        </div>

        <div>
          <Label htmlFor="content" className="mb-1 block dark:text-gray-300">Content (Markdown) <span className="text-red-500">*</span></Label>
          <Textarea id="content" name="content" value={formData.content} onChange={handleChange} rows={12} placeholder="Detailed notes, code snippets, decisions, etc." required className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <Label htmlFor="entry_type" className="mb-1 block dark:text-gray-300">Entry Type</Label>
            <Select name="entry_type" value={formData.entry_type} onValueChange={(value) => handleSelectChange("entry_type", value)} disabled={isLoading}>
              <SelectTrigger className="dark:bg-gray-700 dark:border-gray-600"><SelectValue placeholder="Select type" /></SelectTrigger>
              <SelectContent className="dark:bg-gray-700 dark:text-white">
                {entryTypes.map(type => <SelectItem key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="tags" className="mb-1 block dark:text-gray-300">Tags <span className="text-xs">(comma-separated)</span></Label>
            <Input id="tags" name="tags" type="text" value={Array.isArray(formData.tags) ? formData.tags.join(', ') : ""} onChange={handleTagsChange} placeholder="e.g., frontend, planning, bugfix" className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <Label htmlFor="project_id" className="mb-1 block dark:text-gray-300">Project ID <span className="text-xs">(Optional)</span></Label>
            <Input id="project_id" name="project_id" type="number" value={formData.project_id || ""} onChange={handleChange} placeholder="Link to a project" className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} />
          </div>
          <div>
            <Label htmlFor="task_id" className="mb-1 block dark:text-gray-300">Task ID <span className="text-xs">(Optional)</span></Label>
            <Input id="task_id" name="task_id" type="number" value={formData.task_id || ""} onChange={handleChange} placeholder="Link to a task" className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} />
          </div>
        </div>

        <div className="pt-4">
          <Button type="submit" className="w-full bg-purple-500 hover:bg-purple-600 text-white font-semibold py-3 text-lg rounded-md" disabled={isLoading}>
            {isLoading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <BookText className="mr-2 h-5 w-5" />}
            {isLoading ? "Saving Entry..." : "Save DevLog Entry"}
          </Button>
        </div>
      </form>
    </div>
  );
}
