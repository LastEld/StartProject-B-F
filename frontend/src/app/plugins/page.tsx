"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  listPlugins,
  PluginRead,
  PluginFilters,
  restorePlugin,
  activatePlugin,
  deactivatePlugin,
  getActivePluginsSummary, // Added
  PluginShort // Added
} from "../../lib/api";
import PluginCard from "../../components/PluginCard"; // Using the actual PluginCard
import { PlusCircle, Plug, Search, X, Info } from "lucide-react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
// Checkbox was not used in the final filter for status, using Select instead
// import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";


export default function PluginsListPage() {
  const [plugins, setPlugins] = useState<PluginRead[]>([]);
  const [summary, setSummary] = useState<PluginShort[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<PluginFilters>({
    is_active: undefined,
    subscription_level: "",
    tag: "",
  });
  // const { currentRole } = useAuth();
  const isAdmin = true; // Placeholder

  const fetchPluginsAndSummary = useCallback(async () => {
    setLoading(true);
    setLoadingSummary(true);
    setError(null);
    const token = localStorage.getItem("access_token");

    try {
      const pluginsData = await listPlugins(filters, token ?? undefined);
      setPlugins(pluginsData);
    } catch (err: any) {
      setPlugins([]);
      setError(err.message || "Failed to fetch plugins.");
    } finally {
      setLoading(false);
    }

    try {
      const summaryData = await getActivePluginsSummary(token ?? undefined);
      setSummary(summaryData);
    } catch (err: any) {
      console.error("Failed to fetch plugins summary:", err);
      setSummary(null);
    } finally {
      setLoadingSummary(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchPluginsAndSummary();
  }, [fetchPluginsAndSummary]);

  const handleFilterChange = (key: keyof PluginFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleBooleanFilterChange = (key: keyof PluginFilters, checked: boolean | string) => {
    if (checked === "any" || checked === "") {
      setFilters(prev => ({ ...prev, [key]: undefined }));
    } else {
      setFilters(prev => ({ ...prev, [key]: typeof checked === 'string' ? (checked === "true") : checked }));
    }
  };

  const handleResetFilters = () => {
    setFilters({ is_active: undefined, subscription_level: "", tag: "" });
  };

  const handlePluginAction = async (action: 'restore' | 'activate' | 'deactivate', pluginId: any) => {
    if (!isAdmin) {
      setError("Unauthorized: This action is for administrators only.");
      return;
    }
    const token = localStorage.getItem("access_token");
    if (!token) { setError("Authentication required."); return; }

    let actionFunc;
    switch(action) {
      case 'restore': actionFunc = restorePlugin; break;
      case 'activate': actionFunc = activatePlugin; break;
      case 'deactivate': actionFunc = deactivatePlugin; break;
      default: return;
    }

    try {
      await actionFunc(pluginId, token);
      fetchPluginsAndSummary();
    } catch (err: any) {
      setError(err.message || `Failed to ${action} plugin.`);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
        <h1 className="text-3xl font-bold flex items-center gap-3 text-gray-800 dark:text-white">
          <Plug className="w-8 h-8 text-teal-500" /> Plugins
        </h1>
        {isAdmin && (
          <Link href="/plugins/new" legacyBehavior>
            <Button asChild size="lg" className="bg-teal-500 hover:bg-teal-600 text-white">
              <a><PlusCircle className="w-6 h-6 mr-2" /> Register New Plugin</a>
            </Button>
          </Link>
        )}
      </div>

      <Card className="mb-8 dark:bg-gray-800">
        <CardHeader>
          <CardTitle className="text-xl flex items-center dark:text-white"><Info className="w-5 h-5 mr-2 text-teal-400"/>Active Plugins Summary</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingSummary && <p className="dark:text-gray-400">Loading summary...</p>}
          {error && !loadingSummary && <p className="text-red-500">Could not load summary.</p>}
          {!loadingSummary && summary && summary.length > 0 && (
            <ul className="list-disc pl-5 space-y-1 dark:text-gray-300">
              {summary.map(p => <li key={p.id || p.name}>{p.name} (v{p.version})</li>)}
            </ul>
          )}
          {!loadingSummary && summary && summary.length === 0 && <p className="dark:text-gray-400">No active plugins found or summary unavailable.</p>}
        </CardContent>
      </Card>

      {isAdmin && (
        <div className="mb-8 p-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg border dark:border-gray-700">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <Label htmlFor="is_active-plugin" className="dark:text-gray-300">Status</Label>
              <Select value={filters.is_active === undefined ? "any" : (filters.is_active ? "true" : "false")} onValueChange={(value) => handleBooleanFilterChange("is_active", value)}>
                <SelectTrigger id="is_active-plugin" className="mt-1 dark:bg-gray-700 dark:border-gray-600"><SelectValue /></SelectTrigger>
                <SelectContent className="dark:bg-gray-700 dark:text-white">
                  <SelectItem value="any">Any Status</SelectItem>
                  <SelectItem value="true">Active</SelectItem>
                  <SelectItem value="false">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="subscription_level-plugin" className="dark:text-gray-300">Subscription Level</Label>
              <Input id="subscription_level-plugin" type="text" placeholder="e.g., free, premium" value={filters.subscription_level || ""} onChange={(e) => handleFilterChange("subscription_level", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div>
              <Label htmlFor="tag-plugin" className="dark:text-gray-300">Tag</Label>
              <Input id="tag-plugin" type="text" placeholder="Filter by tag" value={filters.tag || ""} onChange={(e) => handleFilterChange("tag", e.target.value)} className="mt-1 dark:bg-gray-700 dark:border-gray-600" />
            </div>
            <div className="flex items-end space-x-3 col-span-full sm:col-span-1 md:col-start-auto">
              <Button onClick={fetchPluginsAndSummary} className="bg-teal-500 hover:bg-teal-600 text-white w-full sm:w-auto"><Search className="w-4 h-4 mr-2" />Apply</Button>
              <Button onClick={handleResetFilters} variant="outline" className="dark:text-gray-300 dark:border-gray-600 hover:bg-gray-700 w-full sm:w-auto"><X className="w-4 h-4 mr-2" />Reset</Button>
            </div>
          </div>
        </div>
      )}

      {loading && <div className="text-center py-10 dark:text-gray-400">Loading plugins...</div>}
      {error && <Alert variant="destructive" className="mb-6"><AlertCircle className="h-4 w-4" /><AlertTitle>Error</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      {!loading && !error && plugins.length === 0 && <div className="text-center py-10 text-gray-500 dark:text-gray-400">No plugins found.</div>}

      {!loading && !error && plugins.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plugins.map((plugin) => (
            <PluginCard
                key={plugin.id}
                plugin={plugin}
                onAction={handlePluginAction}
                isAdmin={isAdmin}
            />
          ))}
        </div>
      )}
    </div>
  );
}
