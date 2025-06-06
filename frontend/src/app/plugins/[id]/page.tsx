"use client";

import React, { useEffect, useState, ChangeEvent, FormEvent, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getPlugin,
  updatePlugin,
  deletePlugin,
  restorePlugin,
  activatePlugin,
  deactivatePlugin,
  runPluginAction,
  PluginRead,
  PluginUpdate,
} from "../../../lib/api";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"; // For actions
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Loader2, Edit3, Trash2, Save, XCircle, Info, Brain, CalendarDays, TagIcon as Tag, ArrowLeft, ArchiveRestore, Zap, PowerOff, Settings2, Terminal, ShieldCheck, Users, CheckCircle
} from "lucide-react";
import ReactMarkdown from 'react-markdown'; // If description or other fields use Markdown

const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try { return new Date(dateString).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch (e) { return "Invalid Date"; }
};

export default function PluginDetailPage() {
  const router = useRouter();
  const params = useParams();
  const pluginId = params.id as string;

  const [plugin, setPlugin] = useState<PluginRead | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState<PluginUpdate>({});

  // For Run Action
  const [selectedAction, setSelectedAction] = useState<string>("");
  const [projectContext, setProjectContext] = useState<string>('{\n  "projectId": 123,\n  "userId": 456\n}'); // Default example
  const [pluginParams, setPluginParams] = useState<string>('{\n  "param1": "value1"\n}'); // Default example
  const [actionResult, setActionResult] = useState<any>(null);
  const [loadingAction, setLoadingAction] = useState(false);
  const [errorAction, setErrorAction] = useState<string|null>(null);

  const [loading, setLoading] = useState(true);
  const [loadingEdit, setLoadingEdit] = useState(false);
  const [loadingStateChange, setLoadingStateChange] = useState(false); // For activate/deactivate/restore/delete

  const [error, setError] = useState<string | null>(null);
  const [errorEdit, setErrorEdit] = useState<string | null>(null);

  // Placeholder for admin check
  const isAdmin = true; // Replace with actual role check: const { currentRole } = useAuth(); isAdmin = currentRole === 'admin';


  const fetchPluginDetails = useCallback(async () => {
    if (!pluginId) { setError("Plugin ID is missing."); setLoading(false); return; }
    setLoading(true); setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const numericPluginId = parseInt(pluginId);
      if (isNaN(numericPluginId)) { throw new Error("Invalid Plugin ID."); }
      const data = await getPlugin(numericPluginId, token ?? undefined);
      setPlugin(data);
      setEditFormData({ // Initialize form data for editing
        name: data.name,
        description: data.description,
        version: data.version,
        author: data.author,
        tags: data.tags || [],
        // Config schema and actions are complex, usually not directly edited in simple form
        // For is_active and subscription_level_required, these are usually handled by specific actions (activate/deactivate) or admin settings
      });
      if (data.actions && data.actions.length > 0) {
        setSelectedAction(data.actions[0]?.name || ""); // Default to first action if available
      }
    } catch (err: any) { setError(err.message || "Failed to fetch plugin details."); setPlugin(null); }
    finally { setLoading(false); }
  }, [pluginId]);

  useEffect(() => { fetchPluginDetails(); }, [fetchPluginDetails]);

  // Edit handlers
  const handleEditChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setEditFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };
  const handleEditTagsChange = (e: ChangeEvent<HTMLInputElement>) => {
    setEditFormData(prev => ({ ...prev, tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag) }));
  };
  const handleUpdateSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!isAdmin) { setErrorEdit("Unauthorized."); return; }
    if (!editFormData.name?.trim()) { setErrorEdit("Plugin name cannot be empty."); return; }
    setLoadingEdit(true); setErrorEdit(null);
    try {
      const token = localStorage.getItem("access_token");
      const numericPluginId = parseInt(pluginId);
      const updated = await updatePlugin(numericPluginId, editFormData, token ?? undefined);
      setPlugin(updated); setIsEditing(false);
    } catch (err: any) { setErrorEdit(err.message || "Failed to update plugin."); }
    finally { setLoadingEdit(false); }
  };
  const handleCancelEdit = () => {
    setIsEditing(false); setErrorEdit(null);
    if (plugin) setEditFormData({ name: plugin.name, description: plugin.description, /* other fields */ });
  };

  // Plugin state change handlers (activate, deactivate, restore, delete)
  const handlePluginStateChange = async (action: 'activate' | 'deactivate' | 'restore' | 'delete') => {
    if (!plugin || !isAdmin) { setError("Unauthorized or plugin data missing."); return; }
    const numericPluginId = parseInt(pluginId);
    let confirmMessage = "";
    let apiFunc: Function;

    switch(action) {
        case 'activate': apiFunc = activatePlugin; confirmMessage = "Activate this plugin?"; break;
        case 'deactivate': apiFunc = deactivatePlugin; confirmMessage = "Deactivate this plugin?"; break;
        case 'restore': apiFunc = restorePlugin; confirmMessage = "Restore this plugin?"; break;
        case 'delete': apiFunc = deletePlugin; confirmMessage = `Archive this plugin? (Or permanently delete if already archived by backend logic)`; break; // Backend might handle permanent delete if is_deleted is true
        default: return;
    }
    if (!window.confirm(confirmMessage)) return;

    setLoadingStateChange(true); setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const result = await apiFunc(numericPluginId, token ?? undefined);
      if (action === 'delete' && plugin.is_deleted) { // If it was a "permanent delete" action
          router.push("/plugins"); // Redirect after permanent delete
          return;
      }
      setPlugin(result || { ...plugin, is_active: action === 'activate', is_deleted: action === 'delete' ? true : (action === 'restore' ? false : plugin.is_deleted) }); // Optimistic or use result
      fetchPluginDetails(); // Re-fetch to ensure data consistency
    } catch (err: any) { setError(err.message || `Failed to ${action} plugin.`); }
    finally { setLoadingStateChange(false); }
  };

  // Run Action Handler
  const handleRunAction = async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      if (!plugin || !selectedAction || !isAdmin) { setErrorAction("Plugin, action, or authorization missing."); return; }
      setLoadingAction(true); setErrorAction(null); setActionResult(null);
      try {
          const token = localStorage.getItem("access_token");
          let parsedProjectContext = projectContext ? JSON.parse(projectContext) : null;
          let parsedPluginParams = pluginParams ? JSON.parse(pluginParams) : null;

          const result = await runPluginAction(plugin.name, selectedAction, parsedProjectContext, parsedPluginParams, token ?? undefined);
          setActionResult(result);
      } catch (err: any) {
          setErrorAction(err.message || "Failed to run plugin action. Ensure JSON for context/params is valid.");
      } finally {
          setLoadingAction(false);
      }
  };


  if (loading) return <div className="flex justify-center items-center min-h-screen"><Loader2 className="w-12 h-12 animate-spin text-teal-500" /></div>;
  if (error) return <div className="container mx-auto py-10 px-4"><Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Error</AlertTitle><AlertDescription>{error}</AlertDescription><Button onClick={() => router.push("/plugins")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" />Back to Plugins</Button></Alert></div>;
  if (!plugin) return <div className="container mx-auto py-10 px-4 text-center"><p>Plugin not found.</p><Button onClick={() => router.push("/plugins")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" />Back to Plugins</Button></div>;

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex justify-between items-center mb-6">
        <Button onClick={() => router.push("/plugins")} variant="outline" size="sm"><ArrowLeft className="w-4 h-4 mr-2" />Back to Plugins</Button>
        {isAdmin && (<div className="flex space-x-2">
          {!isEditing && !plugin.is_deleted && (<Button onClick={() => setIsEditing(true)} variant="outline"><Edit3 className="w-4 h-4 mr-2" />Edit</Button>)}
          {!isEditing && plugin.is_deleted && (<Button onClick={() => handlePluginStateChange('restore')} variant="outline" className="text-green-600 border-green-500" disabled={loadingStateChange}>{loadingStateChange ? <Loader2 className="w-4 h-4 animate-spin"/> : <ArchiveRestore className="w-4 h-4 mr-2" />}Restore</Button>)}
          {!isEditing && !plugin.is_deleted && (plugin.is_active ? <Button onClick={() => handlePluginStateChange('deactivate')} variant="outline" className="text-orange-600 border-orange-500" disabled={loadingStateChange}>{loadingStateChange ? <Loader2 className="w-4 h-4 animate-spin"/>:<PowerOff className="w-4 h-4 mr-2" />}Deactivate</Button>
                                               : <Button onClick={() => handlePluginStateChange('activate')} variant="outline" className="text-green-600 border-green-500" disabled={loadingStateChange}>{loadingStateChange ? <Loader2 className="w-4 h-4 animate-spin"/>:<Zap className="w-4 h-4 mr-2" />}Activate</Button>)}
          {!isEditing && <Button onClick={() => handlePluginStateChange('delete')} variant="destructive" disabled={loadingStateChange}>{loadingStateChange ? <Loader2 className="w-4 h-4 animate-spin"/>:<Trash2 className="w-4 h-4 mr-2" />}{plugin.is_deleted ? "Delete Permanently" : "Archive"}</Button>}
        </div>)}
      </div>

      {plugin.is_deleted && !isEditing && (<Alert variant="default" className="mb-6 bg-yellow-100 border-yellow-400 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-700"><Info className="h-4 w-4" /><AlertTitle>Archived Plugin</AlertTitle><AlertDescription>This plugin is archived.</AlertDescription></Alert>)}

      {!isEditing ? (
        <Card className="mb-8 dark:bg-gray-800 shadow-lg">
          <CardHeader className="border-b dark:border-gray-700 pb-4">
            <div className="flex justify-between items-center">
                <CardTitle className="text-3xl font-bold dark:text-white">{plugin.name}</CardTitle>
                <Badge className={`${plugin.is_active ? "bg-green-500" : "bg-gray-500"} text-white`}>{plugin.is_active ? "Active" : "Inactive"}</Badge>
            </div>
            <CardDescription className="dark:text-gray-400 pt-1">Version {plugin.version || "N/A"} by {plugin.author || "Unknown Author"}</CardDescription>
            {plugin.subscription_level_required && <p className="text-xs dark:text-blue-400 flex items-center mt-1"><ShieldCheck className="w-3 h-3 mr-1"/>Requires: {plugin.subscription_level_required} subscription</p>}
          </CardHeader>
          <CardContent className="pt-6">
            <h3 className="text-lg font-semibold mb-2 dark:text-white">Description</h3>
            <ReactMarkdown className="prose dark:prose-invert max-w-none mb-6">{plugin.description || "No description available."}</ReactMarkdown>

            {plugin.config_schema && (
              <>
                <h3 className="text-lg font-semibold mb-2 dark:text-white">Configuration Schema</h3>
                <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-3 rounded-md overflow-x-auto mb-6 dark:text-gray-300">{JSON.stringify(plugin.config_schema, null, 2)}</pre>
              </>
            )}
            {plugin.actions && plugin.actions.length > 0 && (
                <>
                <h3 className="text-lg font-semibold mb-2 dark:text-white">Available Actions</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-6">
                    {plugin.actions.map((act: any, idx: number) => <Badge key={idx} variant="outline" className="dark:border-gray-600 dark:text-gray-300"><Settings2 className="w-3 h-3 mr-1"/>{act.name}</Badge>)}
                </div>
                </>
            )}
          </CardContent>
          <CardFooter className="border-t dark:border-gray-700 pt-4 flex flex-wrap gap-2">
            {plugin.tags?.map((tag: string | {name: string}) => <Badge key={typeof tag === 'string' ? tag : tag.name} variant="secondary"><Tag className="w-3 h-3 mr-1"/>{typeof tag === 'string' ? tag : tag.name}</Badge>)}
          </CardFooter>
        </Card>
      ) : ( // EDITING MODE
        isAdmin && <Card className="my-8 dark:bg-gray-800 shadow-xl">
          <CardHeader><CardTitle className="text-2xl font-semibold dark:text-white">Edit Plugin</CardTitle></CardHeader>
          <CardContent>
            {errorEdit && <Alert variant="destructive" className="mb-4"><AlertCircle className="h-4 w-4" /><AlertTitle>Update Error</AlertTitle><AlertDescription>{errorEdit}</AlertDescription></Alert>}
            <form onSubmit={handleUpdateSubmit} className="space-y-6">
              <div><Label htmlFor="name-edit" className="dark:text-gray-300">Name <span className="text-red-500">*</span></Label><Input id="name-edit" name="name" value={editFormData.name || ""} onChange={handleEditChange} required className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
              <div><Label htmlFor="description-edit" className="dark:text-gray-300">Description</Label><Textarea id="description-edit" name="description" value={editFormData.description || ""} onChange={handleEditChange} rows={5} className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
              <div className="grid md:grid-cols-2 gap-4">
                <div><Label htmlFor="version-edit" className="dark:text-gray-300">Version</Label><Input id="version-edit" name="version" value={editFormData.version || ""} onChange={handleEditChange} className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
                <div><Label htmlFor="author-edit" className="dark:text-gray-300">Author</Label><Input id="author-edit" name="author" value={editFormData.author || ""} onChange={handleEditChange} className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
              </div>
              <div><Label htmlFor="tags-edit" className="dark:text-gray-300">Tags <span className="text-xs">(comma-separated)</span></Label><Input id="tags-edit" name="tags" value={Array.isArray(editFormData.tags) ? editFormData.tags.join(", ") : ""} onChange={handleEditTagsChange} className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
              {/* Note: is_active, subscription_level_required, config_schema, actions are typically not edited this way. */}
              <div className="flex justify-end space-x-3 pt-4">
                <Button type="button" onClick={handleCancelEdit} variant="outline" className="dark:border-gray-600" disabled={loadingEdit}><XCircle className="w-4 h-4 mr-2" />Cancel</Button>
                <Button type="submit" className="bg-teal-500 hover:bg-teal-600 text-white" disabled={loadingEdit}>{loadingEdit ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}Save Changes</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Run Action Section (Admin Only) */}
      {isAdmin && !isEditing && plugin && plugin.actions && plugin.actions.length > 0 && !plugin.is_deleted && plugin.is_active && (
        <Card className="my-8 dark:bg-gray-800 shadow-lg">
          <CardHeader><CardTitle className="text-2xl font-semibold dark:text-white flex items-center"><Terminal className="w-6 h-6 mr-2 text-teal-400"/>Run Plugin Action</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleRunAction} className="space-y-4">
              <div>
                <Label htmlFor="action-select" className="dark:text-gray-300">Select Action</Label>
                <Select value={selectedAction} onValueChange={setSelectedAction}>
                  <SelectTrigger id="action-select" className="mt-1 dark:bg-gray-700 dark:border-gray-600"><SelectValue placeholder="Choose an action" /></SelectTrigger>
                  <SelectContent className="dark:bg-gray-700 dark:text-white">
                    {plugin.actions.map((act: any, idx: number) => <SelectItem key={idx} value={act.name}>{act.name} - {act.description}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div><Label htmlFor="projectContext-area" className="dark:text-gray-300">Project Context (JSON)</Label><Textarea id="projectContext-area" value={projectContext} onChange={(e) => setProjectContext(e.target.value)} rows={5} placeholder='e.g., { "projectId": 1 }' className="mt-1 dark:bg-gray-700 dark:border-gray-600 font-mono text-xs" /></div>
              <div><Label htmlFor="pluginParams-area" className="dark:text-gray-300">Plugin Parameters (JSON)</Label><Textarea id="pluginParams-area" value={pluginParams} onChange={(e) => setPluginParams(e.target.value)} rows={5} placeholder='e.g., { "query": "find users" }' className="mt-1 dark:bg-gray-700 dark:border-gray-600 font-mono text-xs" /></div>
              {errorAction && <Alert variant="destructive"><AlertCircle className="h-4 w-4"/><AlertDescription>{errorAction}</AlertDescription></Alert>}
              <Button type="submit" className="bg-teal-500 hover:bg-teal-600 text-white" disabled={loadingAction}>{loadingAction ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="w-4 h-4 mr-2" />}Run Action</Button>
            </form>
            {actionResult !== null && (
              <div className="mt-4">
                <h4 className="font-semibold dark:text-white">Action Result:</h4>
                <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-3 rounded-md overflow-x-auto dark:text-gray-300">{JSON.stringify(actionResult, null, 2)}</pre>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
