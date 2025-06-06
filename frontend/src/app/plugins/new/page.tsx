"use client";

import React, { useState, ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createPlugin, PluginCreate } from "../../../lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { AlertCircle, Loader2, Plug, ArrowLeft } from "lucide-react";

// Placeholder for admin check - in a real app, use auth context
const useIsAdmin = () => {
  // const { currentRole } = useAuth(); return currentRole === 'admin';
  return true;
};

const initialFormData: PluginCreate = {
  name: "",
  description: "",
  version: "0.1.0",
  author: "",
  tags: [],
  is_active: false,
  subscription_level_required: "free",
  config_schema: {}, // Default to empty object, expect JSON input
  actions: [],       // Default to empty array, expect JSON input
};

export default function CreatePluginPage() {
  const router = useRouter();
  const isAdmin = useIsAdmin();
  const [formData, setFormData] = useState<PluginCreate>(initialFormData);
  const [configSchemaJson, setConfigSchemaJson] = useState<string>("{}");
  const [actionsJson, setActionsJson] = useState<string>("[]");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    if (type === 'checkbox') {
        const checked = (e.target as HTMLInputElement).checked;
        setFormData(prev => ({ ...prev, [name]: checked }));
    } else {
        setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleSelectChange = (name: keyof PluginCreate, value: string) => {
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleTagsChange = (e: ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag) }));
  };

  const handleJsonChange = (setter: React.Dispatch<React.SetStateAction<string>>, value: string) => {
    setter(value);
    // Basic validation feedback could be added here if desired
  };


  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!isAdmin) { setError("Unauthorized: Only admins can create plugins."); return; }
    if (!formData.name.trim()) { setError("Plugin name is required."); return; }

    let parsedConfigSchema = {};
    let parsedActions = [];
    try {
        parsedConfigSchema = JSON.parse(configSchemaJson);
    } catch (jsonError) {
        setError("Invalid JSON in Configuration Schema. Please correct it.");
        return;
    }
    try {
        parsedActions = JSON.parse(actionsJson);
        if (!Array.isArray(parsedActions)) throw new Error("Actions must be a JSON array.");
    } catch (jsonError: any) {
        setError(jsonError.message || "Invalid JSON in Actions. Please correct it.");
        return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem("access_token");
      const dataToSubmit: PluginCreate = {
        ...formData,
        config_schema: parsedConfigSchema,
        actions: parsedActions,
      };

      const newPlugin = await createPlugin(dataToSubmit, token ?? undefined);

      if (newPlugin && newPlugin.id) {
        router.push(`/plugins/${newPlugin.id}`);
      } else {
        router.push("/plugins");
      }
    } catch (err: any) {
      setError(err.message || "An unknown error occurred while creating the plugin.");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAdmin && typeof window !== 'undefined') { // Check typeof window for SSR safety
    // router.push('/'); // Or a specific unauthorized page
    return <div className="container mx-auto py-10 px-4 text-center"><p className="text-red-500">Access Denied. Admin only.</p></div>;
  }


  return (
    <div className="container mx-auto max-w-3xl py-12 px-4">
      <Button onClick={() => router.push("/plugins")} variant="outline" size="sm" className="mb-6 dark:text-gray-300 dark:border-gray-600"><ArrowLeft className="w-4 h-4 mr-2" />Back to Plugins</Button>
      <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-10 text-center flex items-center justify-center">
        <Plug className="w-8 h-8 mr-3 text-teal-500" /> Register New Plugin
      </h1>
      <p className="text-center text-sm text-yellow-600 dark:text-yellow-400 mb-8 bg-yellow-50 dark:bg-yellow-900/30 p-3 rounded-md border border-yellow-300 dark:border-yellow-700">
        <AlertCircle className="inline w-4 h-4 mr-1.5" />This is an admin-only page. Ensure you have the necessary permissions.
      </p>

      {error && (
        <div className="mb-6 p-4 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-lg flex items-center shadow">
          <AlertCircle className="w-5 h-5 mr-3" /> <p className="text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8 bg-white dark:bg-gray-800 p-8 rounded-xl shadow-xl border dark:border-gray-700">
        <div><Label htmlFor="name" className="mb-1 block dark:text-gray-300">Plugin Name <span className="text-red-500">*</span></Label><Input id="name" name="name" value={formData.name} onChange={handleChange} required className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} /></div>
        <div><Label htmlFor="description" className="mb-1 block dark:text-gray-300">Description</Label><Textarea id="description" name="description" value={formData.description} onChange={handleChange} rows={3} className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} /></div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div><Label htmlFor="version" className="mb-1 block dark:text-gray-300">Version</Label><Input id="version" name="version" value={formData.version} onChange={handleChange} placeholder="e.g., 1.0.0" className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} /></div>
            <div><Label htmlFor="author" className="mb-1 block dark:text-gray-300">Author</Label><Input id="author" name="author" value={formData.author} onChange={handleChange} placeholder="Your name or organization" className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} /></div>
        </div>

        <div><Label htmlFor="tags" className="mb-1 block dark:text-gray-300">Tags <span className="text-xs">(comma-separated)</span></Label><Input id="tags" name="tags" value={Array.isArray(formData.tags) ? formData.tags.join(', ') : ""} onChange={handleTagsChange} placeholder="e.g., utility, ai, data_processing" className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} /></div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div>
                <Label htmlFor="subscription_level_required" className="mb-1 block dark:text-gray-300">Required Subscription</Label>
                <Select name="subscription_level_required" value={formData.subscription_level_required} onValueChange={(value) => handleSelectChange("subscription_level_required", value)} disabled={isLoading}>
                    <SelectTrigger className="dark:bg-gray-700 dark:border-gray-600"><SelectValue /></SelectTrigger>
                    <SelectContent className="dark:bg-gray-700 dark:text-white">
                        <SelectItem value="free">Free</SelectItem><SelectItem value="basic">Basic</SelectItem><SelectItem value="premium">Premium</SelectItem><SelectItem value="enterprise">Enterprise</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <div className="flex items-center space-x-2 pt-6">
                <Checkbox id="is_active" name="is_active" checked={formData.is_active} onCheckedChange={(checked) => setFormData(prev => ({...prev, is_active: Boolean(checked)}))} className="dark:border-gray-600" disabled={isLoading} />
                <Label htmlFor="is_active" className="dark:text-gray-300">Active on Creation</Label>
            </div>
        </div>

        <div>
            <Label htmlFor="config_schema" className="mb-1 block dark:text-gray-300">Configuration Schema (JSON)</Label>
            <Textarea id="config_schema" value={configSchemaJson} onChange={(e) => handleJsonChange(setConfigSchemaJson, e.target.value)} rows={8} placeholder='e.g., { "apiKey": { "type": "string", "required": true } }' className="font-mono text-xs dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} />
        </div>
        <div>
            <Label htmlFor="actions" className="mb-1 block dark:text-gray-300">Actions (JSON Array)</Label>
            <Textarea id="actions" value={actionsJson} onChange={(e) => handleJsonChange(setActionsJson, e.target.value)} rows={8} placeholder='e.g., [ { "name": "runReport", "description": "Generates a report.", "params_schema": {} } ]' className="font-mono text-xs dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} />
        </div>

        <div className="pt-4">
          <Button type="submit" className="w-full bg-teal-500 hover:bg-teal-600 text-white font-semibold py-3 text-lg" disabled={isLoading}>
            {isLoading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Plug className="mr-2 h-5 w-5" />}
            {isLoading ? "Registering Plugin..." : "Register Plugin"}
          </Button>
        </div>
      </form>
    </div>
  );
}
