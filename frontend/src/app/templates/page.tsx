"use client";

import React, { useEffect, useState, useCallback } from "react";
import { listTemplates, TemplateRead, TemplateFilters, restoreTemplate } from "../../lib/api";
import TemplateCard from "../../components/TemplateCard"; // Using the actual TemplateCard
import { PlusCircle, LayoutTemplate, Search, X, ArchiveRestore, Loader2, AlertCircle, Copy } from "lucide-react"; // Added Copy for clone
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
// Badge is now handled inside TemplateCard
// import { Badge } from "@/components/ui/badge";


export default function TemplatesListPage() {
  const [templates, setTemplates] = useState<TemplateRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TemplateFilters>({
    name: "",
    is_active: undefined,
    is_private: undefined,
    subscription_level: "",
    tag: "",
    author_id: undefined,
    is_deleted: false,
  });

  // Placeholder for role check: const { isAdmin } = useAuth();
  const isAdmin = true;

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const activeFilters: Partial<TemplateFilters> = {};
      for (const [key, value] of Object.entries(filters)) {
        if (value !== undefined && value !== "") {
          (activeFilters as any)[key] = value;
        }
      }
      const templatesData = await listTemplates(activeFilters, token ?? undefined);
      setTemplates(templatesData);
    } catch (err: any) {
      setTemplates([]);
      setError(err.message || "Failed to fetch templates.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleFilterChange = (key: keyof TemplateFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleNumericFilterChange = (key: keyof TemplateFilters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value === "" ? undefined : Number(value)}));
  };

  const handleBooleanSelectChange = (key: keyof TemplateFilters, value: string) => {
    if (value === "any") {
      setFilters(prev => ({ ...prev, [key]: undefined }));
    } else {
      setFilters(prev => ({ ...prev, [key]: value === "true" }));
    }
  };

  const handleResetFilters = () => {
    setFilters({ name: "", is_active: undefined, is_private: undefined, subscription_level: "", tag: "", author_id: undefined, is_deleted: false });
  };

  const handleRestoreTemplate = async (templateId: number) => {
    // TODO: Add admin/author check if necessary
    const token = localStorage.getItem("access_token");
    if (!token) { setError("Authentication required."); return; }

    try {
      await restoreTemplate(templateId, token);
      fetchTemplates(); // Refresh list
    } catch (err: any) {
      setError(err.message || `Failed to restore template.`);
    }
  };

  const handleCloneTemplateRedirect = (templateId: number) => {
    // For list page, a direct clone might be too complex.
    // Usually, clone is initiated from the detail page or a specific "clone" action UI.
    // Here, we can redirect to the detail page with a query param to open the clone modal,
    // or simply alert that cloning is done from the detail page.
    // For now, alert, or redirect to detail page.
    // router.push(`/templates/${templateId}?action=clone`);
    alert(`Cloning for template ID ${templateId} would typically be handled on its detail page or a dedicated clone UI.`);
  };


  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
        <h1 className="text-3xl font-bold flex items-center gap-3 text-gray-800 dark:text-white">
          <LayoutTemplate className="w-8 h-8 text-sky-500" /> Templates
        </h1>
        <Link href="/templates/new" legacyBehavior>
          <Button asChild size="lg" className="bg-sky-500 hover:bg-sky-600 text-white">
            <a><PlusCircle className="w-6 h-6 mr-2" /> Create New Template</a>
          </Button>
        </Link>
      </div>

      <div className="mb-8 p-4 md:p-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg border dark:border-gray-700">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-6 gap-y-4">
          <div><Label htmlFor="name-template" className="dark:text-gray-300 text-sm">Name</Label><Input id="name-template" type="text" placeholder="Search by name..." value={filters.name || ""} onChange={(e) => handleFilterChange("name", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600"/></div>
          <div><Label htmlFor="tag-template" className="dark:text-gray-300 text-sm">Tag</Label><Input id="tag-template" type="text" placeholder="Filter by tag" value={filters.tag || ""} onChange={(e) => handleFilterChange("tag", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600"/></div>
          <div><Label htmlFor="author_id-template" className="dark:text-gray-300 text-sm">Author ID</Label><Input id="author_id-template" type="number" placeholder="Filter by Author ID" value={filters.author_id || ""} onChange={(e) => handleNumericFilterChange("author_id", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600"/></div>
          <div><Label htmlFor="subscription_level-template" className="dark:text-gray-300 text-sm">Subscription Level</Label><Input id="subscription_level-template" type="text" placeholder="e.g., free, premium" value={filters.subscription_level || ""} onChange={(e) => handleFilterChange("subscription_level", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600"/></div>

          <div><Label htmlFor="is_active-template" className="dark:text-gray-300 text-sm">Status</Label>
            <Select value={filters.is_active === undefined ? "any" : (filters.is_active ? "true" : "false")} onValueChange={(value) => handleBooleanSelectChange("is_active", value)}>
              <SelectTrigger id="is_active-template" className="mt-1 dark:bg-gray-700 dark:border-gray-600"><SelectValue /></SelectTrigger>
              <SelectContent className="dark:bg-gray-700 dark:text-white"><SelectItem value="any">Any Status</SelectItem><SelectItem value="true">Active</SelectItem><SelectItem value="false">Inactive</SelectItem></SelectContent>
            </Select>
          </div>
          <div><Label htmlFor="is_private-template" className="dark:text-gray-300 text-sm">Visibility</Label>
            <Select value={filters.is_private === undefined ? "any" : (filters.is_private ? "true" : "false")} onValueChange={(value) => handleBooleanSelectChange("is_private", value)}>
              <SelectTrigger id="is_private-template" className="mt-1 dark:bg-gray-700 dark:border-gray-600"><SelectValue /></SelectTrigger>
              <SelectContent className="dark:bg-gray-700 dark:text-white"><SelectItem value="any">Any Visibility</SelectItem><SelectItem value="true">Private</SelectItem><SelectItem value="false">Public</SelectItem></SelectContent>
            </Select>
          </div>
          <div className="flex items-center space-x-2 pt-7">
            <Checkbox id="is_deleted-template" checked={filters.is_deleted || false} onCheckedChange={(checked) => handleFilterChange("is_deleted", Boolean(checked))} className="dark:border-gray-600 data-[state=checked]:bg-sky-500"/>
            <Label htmlFor="is_deleted-template" className="dark:text-gray-300 text-sm font-medium">Show Archived</Label>
          </div>
          <div className="flex items-end space-x-3 col-span-full sm:col-span-1 md:col-start-auto">
            <Button onClick={fetchTemplates} className="bg-sky-500 hover:bg-sky-600 text-white w-full sm:w-auto"><Search className="w-4 h-4 mr-2"/>Apply</Button>
            <Button onClick={handleResetFilters} variant="outline" className="dark:text-gray-300 dark:border-gray-600 hover:bg-gray-700 w-full sm:w-auto"><X className="w-4 h-4 mr-2"/>Reset</Button>
          </div>
        </div>
      </div>

      {loading && <div className="text-center py-10 dark:text-gray-400"><Loader2 className="w-8 h-8 animate-spin mx-auto text-sky-500"/>Loading templates...</div>}
      {error && <Alert variant="destructive" className="mb-6"><AlertCircle className="h-4 w-4" /> <AlertTitle>Error</AlertTitle> <AlertDescription>{error}</AlertDescription></Alert>}
      {!loading && !error && templates.length === 0 && (
        <div className="text-center py-16 text-gray-500 dark:text-gray-400">
          <LayoutTemplate className="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500"/>
          <h2 className="text-xl font-semibold mb-2">No Templates Found</h2>
          <p className="text-sm">{Object.values(filters).some(v => v !== undefined && v !== "" && v !== false) ? "No templates match your current filters." : "Create a new template to get started."}</p>
        </div>
      )}
      {!loading && !error && templates.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {templates.map((template) => (
            <TemplateCard
                key={template.id}
                template={template}
                onRestore={filters.is_deleted && template.is_deleted ? handleRestoreTemplate : undefined}
                onClone={handleCloneTemplateRedirect}
                // isAdmin={isAdmin} // Pass if needed for card-level actions
            />
          ))}
        </div>
      )}
    </div>
  );
}
