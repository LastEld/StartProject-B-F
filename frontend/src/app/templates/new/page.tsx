"use client";

import React, { useState, ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createTemplate, TemplateCreate } from "../../../lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { AlertCircle, Loader2, LayoutTemplate, ArrowLeft } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";


// Placeholder for auth context/hook
const useAuth = () => ({ token: typeof window !== "undefined" ? localStorage.getItem("access_token") : null });

const initialFormData: TemplateCreate = {
  name: "",
  description: "",
  content: "{\n  \"version\": 1,\n  \"tasks\": [\n    {\n      \"name\": \"Sample Task 1\",\n      \"description\": \"Do this first.\",\n      \"status\": \"todo\",\n      \"priority\": 3\n    }\n  ]\n}", // Default example content
  is_active: true,
  is_private: false,
  tags: [],
  subscription_level_required: "free",
};

export default function CreateTemplatePage() {
  const router = useRouter();
  const { token } = useAuth();
  const [formData, setFormData] = useState<TemplateCreate>(initialFormData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleCheckboxChange = (name: keyof TemplateCreate, checked: boolean | string ) => {
     setFormData(prev => ({ ...prev, [name]: Boolean(checked) }));
  };

  const handleSelectChange = (name: keyof TemplateCreate, value: string) => {
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleTagsChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag) }));
  };

  const handleContentChange = (value: string) => {
    setFormData(prev => ({ ...prev, content: value }));
  };


  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!formData.name.trim()) { setError("Template name is required."); return; }
    if (!formData.content.trim()) { setError("Content (JSON structure) is required."); return; }

    let parsedContent;
    try {
        parsedContent = JSON.parse(formData.content);
    } catch (jsonError) {
        setError("Content is not valid JSON. Please provide a valid JSON structure for the template.");
        return;
    }

    setIsLoading(true);
    setError(null);

    try {
      if (!token) throw new Error("Authentication token not found. Please log in.");
      const dataToSubmit: TemplateCreate = { ...formData, content: parsedContent };
      const newTemplate = await createTemplate(dataToSubmit, token);

      if (newTemplate && newTemplate.id) {
        router.push(`/templates/${newTemplate.id}`);
      } else {
        router.push("/templates");
      }
    } catch (err: any) {
      setError(err.message || "An unknown error occurred while creating the template.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-2xl py-12 px-4">
      <Button onClick={() => router.push("/templates")} variant="outline" size="sm" className="mb-6 dark:text-gray-300 dark:border-gray-600">
        <ArrowLeft className="w-4 h-4 mr-2" />Back to Templates List
      </Button>
      <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-10 text-center flex items-center justify-center">
        <LayoutTemplate className="w-8 h-8 mr-3 text-sky-500" /> Create New Template
      </h1>

      {error && (
        <div className="mb-6 p-4 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-lg flex items-center shadow">
          <AlertCircle className="w-5 h-5 mr-3" /> <p className="text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 p-8 rounded-xl shadow-xl border dark:border-gray-700">
        <div><Label htmlFor="name" className="mb-1 block dark:text-gray-300">Template Name <span className="text-red-500">*</span></Label><Input id="name" name="name" value={formData.name} onChange={handleChange} placeholder="e.g., Standard Web Project, Blog Post Structure" required className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} /></div>
        <div><Label htmlFor="description" className="mb-1 block dark:text-gray-300">Description</Label><Textarea id="description" name="description" value={formData.description || ""} onChange={handleChange} rows={3} placeholder="Briefly describe what this template is for." className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} /></div>
        <div><Label htmlFor="content" className="mb-1 block dark:text-gray-300">Content (JSON Structure) <span className="text-red-500">*</span></Label><Textarea id="content" name="content" value={formData.content} onChange={(e) => handleContentChange(e.target.value)} rows={12} placeholder='Define tasks, structure, etc., as a JSON object.' required className="font-mono text-xs dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} /></div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div><Label htmlFor="tags" className="mb-1 block dark:text-gray-300">Tags <span className="text-xs">(comma-separated)</span></Label><Input id="tags" name="tags" value={Array.isArray(formData.tags) ? formData.tags.join(', ') : ""} onChange={handleTagsChange} placeholder="e.g., web, marketing, content" className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} /></div>
            <div>
                <Label htmlFor="subscription_level_required" className="mb-1 block dark:text-gray-300">Required Subscription</Label>
                <Select name="subscription_level_required" value={formData.subscription_level_required || "free"} onValueChange={(value) => handleSelectChange("subscription_level_required", value)} disabled={isLoading}>
                    <SelectTrigger className="dark:bg-gray-700 dark:border-gray-600"><SelectValue /></SelectTrigger>
                    <SelectContent className="dark:bg-gray-700 dark:text-white">
                        <SelectItem value="free">Free</SelectItem><SelectItem value="basic">Basic</SelectItem><SelectItem value="premium">Premium</SelectItem><SelectItem value="enterprise">Enterprise</SelectItem>
                    </SelectContent>
                </Select>
            </div>
        </div>

        <div className="flex items-center space-x-6 pt-2">
            <div className="flex items-center space-x-2"><Checkbox id="is_active" name="is_active" checked={formData.is_active} onCheckedChange={(checked) => handleCheckboxChange("is_active", Boolean(checked))} className="dark:border-gray-600 data-[state=checked]:bg-sky-500" disabled={isLoading} /><Label htmlFor="is_active" className="dark:text-gray-300">Active</Label></div>
            <div className="flex items-center space-x-2"><Checkbox id="is_private" name="is_private" checked={formData.is_private} onCheckedChange={(checked) => handleCheckboxChange("is_private", Boolean(checked))} className="dark:border-gray-600 data-[state=checked]:bg-sky-500" disabled={isLoading} /><Label htmlFor="is_private" className="dark:text-gray-300">Private</Label></div>
        </div>

        <div className="pt-4">
          <Button type="submit" className="w-full bg-sky-500 hover:bg-sky-600 text-white font-semibold py-3 text-lg rounded-md" disabled={isLoading}>
            {isLoading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <PlusCircle className="mr-2 h-5 w-5" />}
            {isLoading ? "Creating Template..." : "Create Template"}
          </Button>
        </div>
      </form>
    </div>
  );
}
