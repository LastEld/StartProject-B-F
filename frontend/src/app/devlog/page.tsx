"use client";

import React, { useEffect, useState, useCallback } from "react";
import { listDevlogs, DevLogRead, DevLogFilters, restoreDevlog } from "../../lib/api";
import DevLogCard from "../../components/DevLogCard";
import { PlusCircle, BookText, Search, X, Loader2 as PageLoaderIcon, AlertCircle as AlertErrorIcon, BookOpen } from "lucide-react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { toast } from "sonner";

export default function DevLogListPage() {
  const [entries, setEntries] = useState<DevLogRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<DevLogFilters>({
    search: "", entry_type: "", project_id: undefined, task_id: undefined,
    author_id: undefined, tag: "", show_archived: false, date_from: "", date_to: "",
  });

  const fetchEntries = useCallback(() => {
    setLoading(true); setError(null);
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    const activeFilters: Partial<DevLogFilters> = {};
    for (const key in filters) {
      if (filters[key as keyof DevLogFilters] !== "" && filters[key as keyof DevLogFilters] !== undefined) {
        (activeFilters as any)[key] = filters[key as keyof DevLogFilters];
      } else if (typeof filters[key as keyof DevLogFilters] === 'boolean') {
         (activeFilters as any)[key] = filters[key as keyof DevLogFilters];
      }
    }

    listDevlogs(activeFilters, token ?? undefined)
      .then(setEntries)
      .catch((err) => {
        setEntries([]);
        const errorMessage = err.message || "Failed to fetch devlog entries.";
        setError(errorMessage);
        toast.error(`Failed to load entries: ${errorMessage}`);
      })
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => { fetchEntries(); }, [fetchEntries]);

  const handleFilterChange = (key: keyof DevLogFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value === "" && ['project_id', 'task_id', 'author_id'].includes(key) ? undefined : value }));
  };

  const handleResetFilters = () => {
    setFilters({ search: "", entry_type: "", project_id: undefined, task_id: undefined, author_id: undefined, tag: "", show_archived: false, date_from: "", date_to: "" });
  };

  const handleRestoreEntry = async (entryId: any) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) { toast.error("Authentication required."); setError("Authentication required."); return; }

    const toastId = toast.loading("Restoring DevLog entry...");
    try {
      await restoreDevlog(entryId, token);
      toast.success("DevLog entry restored successfully!", { id: toastId });
      fetchEntries();
    } catch (err: any) {
      const errorMessage = err.message || "Failed to restore entry.";
      setError(errorMessage); // Keep local error if needed for inline display
      toast.error(`Failed to restore entry: ${errorMessage}`, { id: toastId });
    }
  };

  const entryTypes = ["general", "meeting", "code", "research", "decision", "debug", "release", "issue"];

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
        <h1 className="text-3xl font-bold flex items-center gap-3 text-gray-800 dark:text-white">
          <BookText className="w-8 h-8 text-purple-500" /> DevLog Entries
        </h1>
        <Link href="/devlog/new" legacyBehavior>
          <Button asChild size="lg" className="bg-purple-500 hover:bg-purple-600 text-white">
            <a><PlusCircle className="w-6 h-6 mr-2" /> Create New Entry</a>
          </Button>
        </Link>
      </div>

      <div className="mb-8 p-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg border dark:border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div><Label htmlFor="search-devlog" className="dark:text-gray-300 text-sm">Search</Label><Input id="search-devlog" type="text" placeholder="Title or content..." value={filters.search || ""} onChange={(e) => handleFilterChange("search", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600" /></div>
          <div><Label htmlFor="entry_type-devlog" className="dark:text-gray-300 text-sm">Entry Type</Label><Select value={filters.entry_type || ""} onValueChange={(value) => handleFilterChange("entry_type", value)}><SelectTrigger id="entry_type-devlog" className="mt-1 dark:bg-gray-700 dark:border-gray-600"><SelectValue placeholder="Any Type" /></SelectTrigger><SelectContent className="dark:bg-gray-700 dark:text-white"><SelectItem value="">Any Type</SelectItem>{entryTypes.map(type => <SelectItem key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</SelectItem>)}</SelectContent></Select></div>
          <div><Label htmlFor="project_id-devlog" className="dark:text-gray-300 text-sm">Project ID</Label><Input id="project_id-devlog" type="number" placeholder="Filter by Project ID" value={filters.project_id || ""} onChange={(e) => handleFilterChange("project_id", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600" /></div>
          <div><Label htmlFor="task_id-devlog" className="dark:text-gray-300 text-sm">Task ID</Label><Input id="task_id-devlog" type="number" placeholder="Filter by Task ID" value={filters.task_id || ""} onChange={(e) => handleFilterChange("task_id", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600" /></div>
          <div><Label htmlFor="author_id-devlog" className="dark:text-gray-300 text-sm">Author ID</Label><Input id="author_id-devlog" type="number" placeholder="Filter by Author ID" value={filters.author_id || ""} onChange={(e) => handleFilterChange("author_id", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600" /></div>
          <div><Label htmlFor="tag-devlog" className="dark:text-gray-300 text-sm">Tag</Label><Input id="tag-devlog" type="text" placeholder="Filter by tag..." value={filters.tag || ""} onChange={(e) => handleFilterChange("tag", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600" /></div>
          <div><Label htmlFor="date_from-devlog" className="dark:text-gray-300 text-sm">Date From</Label><Input id="date_from-devlog" type="date" value={filters.date_from || ""} onChange={(e) => handleFilterChange("date_from", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600" /></div>
          <div><Label htmlFor="date_to-devlog" className="dark:text-gray-300 text-sm">Date To</Label><Input id="date_to-devlog" type="date" value={filters.date_to || ""} onChange={(e) => handleFilterChange("date_to", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600" /></div>
          <div className="flex items-center space-x-2 mt-2 md:pt-6"><Checkbox id="show_archived-devlog" checked={filters.show_archived || false} onCheckedChange={(checked) => handleFilterChange("show_archived", Boolean(checked))} className="dark:border-gray-600 data-[state=checked]:bg-purple-500"/><Label htmlFor="show_archived-devlog" className="dark:text-gray-300 text-sm">Show Archived</Label></div>
          <div className="flex items-end space-x-3 col-span-full sm:col-span-1 md:col-start-auto"><Button onClick={fetchEntries} className="bg-purple-500 hover:bg-purple-600 text-white w-full sm:w-auto"><Search className="w-4 h-4 mr-2" /> Apply</Button><Button onClick={handleResetFilters} variant="outline" className="dark:text-gray-300 dark:border-gray-600 hover:bg-gray-700 w-full sm:w-auto"><X className="w-4 h-4 mr-2" /> Reset</Button></div>
        </div>
      </div>

      {loading && <div className="flex flex-col items-center justify-center text-center dark:text-gray-400 py-20"><PageLoaderIcon className="w-12 h-12 animate-spin text-purple-500 mb-4" /><p className="text-lg">Loading DevLog entries...</p></div>}
      {error && !loading && (<Alert variant="destructive" className="mb-6"><AlertErrorIcon className="h-5 w-5" /><AlertTitle className="font-semibold">Error Fetching Entries</AlertTitle><AlertDescription>{error}<br/>Please try again. <Button variant="link" onClick={fetchEntries} className="p-0 h-auto text-red-400 hover:text-red-300">Retry</Button></AlertDescription></Alert>)}
      {!loading && !error && entries.length === 0 && (
        <div className="text-center dark:text-gray-400 py-16 border-2 border-dashed dark:border-gray-700 rounded-xl">
          <BookOpen className="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500"/>
          <h2 className="text-2xl font-semibold mb-2">No DevLog Entries Found</h2>
          <p className="text-md mb-4">{Object.values(filters).some(v => v && v !== false && (typeof v !== 'object' || Object.keys(v).length > 0)) ? "No entries match your current filters." : "Start by creating a new DevLog entry!"}</p>
          <Link href="/devlog/new" legacyBehavior><Button className="bg-purple-500 hover:bg-purple-600 text-white text-lg px-6 py-3"><PlusCircle className="w-5 h-5 mr-2" /> Create First Entry</Button></Link>
        </div>
      )}
      {!loading && !error && entries.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {entries.map((entry) => (
            <DevLogCard
                key={entry.id}
                entry={entry}
                onRestore={filters.show_archived && entry.is_deleted ? handleRestoreEntry : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
