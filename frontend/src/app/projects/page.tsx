"use client";

import React, { useEffect, useState, useCallback } from "react";
import ProjectCard from "../../components/ProjectCard";
import { Folder, PlusCircle, Search, X, Loader2, AlertCircle } from "lucide-react";
import { getProjects, ProjectRead, ProjectFilters, restoreProject } from "../../lib/api";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<ProjectFilters>({
    search: "",
    status: "",
    tag: "",
    priority: undefined,
    is_archived: false,
    deadline_after: "",
    deadline_before: "",
  });

  const fetchProjects = useCallback(() => {
    setLoading(true);
    setError(null);
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    const activeFilters: Partial<ProjectFilters> = {};
    for (const key in filters) {
      if (filters[key as keyof ProjectFilters] !== "" && filters[key as keyof ProjectFilters] !== undefined) {
        (activeFilters as any)[key] = filters[key as keyof ProjectFilters];
      } else if (typeof filters[key as keyof ProjectFilters] === 'boolean') {
         (activeFilters as any)[key] = filters[key as keyof ProjectFilters];
      }
    }

    getProjects(activeFilters, token ?? undefined)
      .then(setProjects)
      .catch((err) => {
        setProjects([]);
        const errorMessage = err.message || "Failed to fetch projects.";
        setError(errorMessage);
        toast.error(`Failed to load projects: ${errorMessage}`);
      })
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleFilterChange = (key: keyof ProjectFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleRestoreProject = async (projectId: any) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) {
      toast.error("Authentication token not found. Please log in.");
      setError("Authentication token not found. Please log in.");
      return;
    }
    const toastId = toast.loading("Restoring project...");
    try {
      await restoreProject(projectId.toString(), token);
      toast.success("Project restored successfully!", { id: toastId });
      fetchProjects();
    } catch (err: any) {
      const errorMessage = err.message || "Failed to restore project.";
      setError(errorMessage); // Keep local error state if needed for inline display
      toast.error(`Failed to restore project: ${errorMessage}`, { id: toastId });
    }
  };

  const handleResetFilters = () => {
    setFilters({
      search: "", status: "", tag: "", priority: undefined, is_archived: false,
      deadline_after: "", deadline_before: "",
    });
  };

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
        <h1 className="text-3xl font-bold flex items-center gap-3 text-gray-800 dark:text-white">
          <Folder className="w-8 h-8 text-blue-500" /> Projects
        </h1>
        <Link href="/projects/new" legacyBehavior>
          <Button asChild size="lg" className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg flex items-center gap-2 transition-colors duration-150 shadow-md hover:shadow-lg">
            <a><PlusCircle className="w-6 h-6" /> Create New Project</a>
          </Button>
        </Link>
      </div>

      {/* Filters Section */}
      <div className="mb-8 p-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div><Label htmlFor="search-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">Search</Label><div className="relative mt-1"><Input id="search-filter" type="text" placeholder="Project name or description..." value={filters.search || ""} onChange={(e) => handleFilterChange("search", e.target.value)} className="pl-10 dark:bg-gray-700 dark:border-gray-600 dark:text-white" /><Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" /></div></div>
          <div><Label htmlFor="status-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">Status</Label><Select value={filters.status || ""} onValueChange={(value) => handleFilterChange("status", value)}><SelectTrigger id="status-filter" className="mt-1 dark:bg-gray-700 dark:border-gray-600 dark:text-white"><SelectValue placeholder="Any Status" /></SelectTrigger><SelectContent className="dark:bg-gray-700 dark:text-white"><SelectItem value="">Any Status</SelectItem><SelectItem value="not_started">Not Started</SelectItem><SelectItem value="in_progress">In Progress</SelectItem><SelectItem value="completed">Completed</SelectItem><SelectItem value="on_hold">On Hold</SelectItem><SelectItem value="cancelled">Cancelled</SelectItem></SelectContent></Select></div>
          <div><Label htmlFor="tag-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">Tag</Label><Input id="tag-filter" type="text" placeholder="Enter tag..." value={filters.tag || ""} onChange={(e) => handleFilterChange("tag", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600 dark:text-white"/></div>
          <div><Label htmlFor="priority-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">Priority</Label><Select value={filters.priority?.toString() || ""} onValueChange={(value) => handleFilterChange("priority", value ? parseInt(value) : undefined)}><SelectTrigger id="priority-filter" className="mt-1 dark:bg-gray-700 dark:border-gray-600 dark:text-white"><SelectValue placeholder="Any Priority" /></SelectTrigger><SelectContent className="dark:bg-gray-700 dark:text-white"><SelectItem value="">Any Priority</SelectItem>{[1, 2, 3, 4, 5].map(p => <SelectItem key={p} value={p.toString()}>{p}</SelectItem>)}</SelectContent></Select></div>
          <div className="flex items-center space-x-2 mt-2 md:mt-0 md:pt-6"><Checkbox id="archived-filter" checked={filters.is_archived || false} onCheckedChange={(checked) => handleFilterChange("is_archived", Boolean(checked))} className="dark:border-gray-600 data-[state=checked]:bg-blue-500"/><Label htmlFor="archived-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">Show Archived</Label></div>
          <div><Label htmlFor="deadline-after-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">Deadline After</Label><Input id="deadline-after-filter" type="date" value={filters.deadline_after || ""} onChange={(e) => handleFilterChange("deadline_after", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600 dark:text-white"/></div>
          <div><Label htmlFor="deadline-before-filter" className="text-sm font-medium text-gray-700 dark:text-gray-300">Deadline Before</Label><Input id="deadline-before-filter" type="date" value={filters.deadline_before || ""} onChange={(e) => handleFilterChange("deadline_before", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600 dark:text-white"/></div>
          <div className="flex items-end space-x-3"><Button onClick={fetchProjects} className="bg-blue-500 hover:bg-blue-600 text-white"><Search className="w-4 h-4 mr-2" /> Apply Filters</Button><Button onClick={handleResetFilters} variant="outline" className="text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"><X className="w-4 h-4 mr-2" /> Reset</Button></div>
        </div>
      </div>

      {loading &&
        <div className="flex flex-col items-center justify-center text-center text-gray-500 dark:text-gray-400 py-20"> {/* Increased py */}
          <Loader2 className="w-12 h-12 animate-spin text-blue-500 mb-4" /> {/* Larger spinner */}
          <p className="text-lg">Loading projects, please wait...</p>
        </div>
      }
      {error && !loading && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-5 w-5" /> {/* Slightly larger icon */}
          <AlertTitle className="font-semibold">Error Fetching Projects</AlertTitle>
          <AlertDescription>
            {error} <br />
            Please try refreshing the page. If the issue persists, contact support.
            <Button variant="outline" size="sm" onClick={fetchProjects} className="mt-3 ml-auto block">Retry</Button>
          </AlertDescription>
        </Alert>
      )}
      {!loading && !error && projects.length === 0 && (
        <div className="text-center text-gray-500 dark:text-gray-400 py-16 border-2 border-dashed dark:border-gray-700 rounded-xl"> {/* Enhanced styling */}
          <Folder className="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500"/>
          <h2 className="text-2xl font-semibold mb-2">No Projects Found</h2>
          <p className="text-md mb-4">
            {Object.values(filters).some(v => v && v !== false && (typeof v !== 'object' || Object.keys(v).length > 0))
              ? "No projects match your current filters. Try adjusting or resetting them."
              : "You haven't created any projects yet. Let's get started!"}
          </p>
          <Link href="/projects/new" legacyBehavior>
            <Button className="bg-blue-500 hover:bg-blue-600 text-white text-lg px-6 py-3">
              <PlusCircle className="w-5 h-5 mr-2" /> Create Your First Project
            </Button>
          </Link>
        </div>
      )}
      {!loading && !error && projects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 xl:gap-8">
          {projects.map((project) => (
            <ProjectCard
              key={project.id || project.name}
              project={project}
              onRestore={filters.is_archived && project.is_archived ? handleRestoreProject : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
