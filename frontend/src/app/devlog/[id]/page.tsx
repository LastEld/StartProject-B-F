"use client";

import React, { useEffect, useState, ChangeEvent, FormEvent, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getDevlog,
  updateDevlog,
  deleteDevlog,
  restoreDevlog,
  summarizeDevlogEntry,
  getDevlogEntryAIContext,
  DevLogRead,
  DevLogUpdate,
  DevLogShort,
  AIContextRead,
  AIContextCreate,
  AIContextUpdate as AIContextUpdateType,
  listAIContexts,
  createAIContext,
  updateAIContext,
  deleteAIContext as deleteAiContextEntry,
} from "../../../lib/api";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from "@/components/ui/dialog";
import {
  Loader2, Edit3, Trash2, Save, XCircle, Info, Brain, CalendarDays, TagIcon as Tag, UserCircle, ArrowLeft, ArchiveRestore, FileText, Users, Zap, Briefcase, CheckCircle as CheckCircleIcon, PlusSquare, AlertCircle as AlertCircleIcon
} from "lucide-react";
import ReactMarkdown from 'react-markdown';
import { toast } from "sonner";

const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try { return new Date(dateString).toLocaleString(undefined, { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch (e) { return "Invalid Date"; }
};

const entryTypes = ["general", "meeting", "code", "research", "decision", "debug", "release", "issue"];

const initialAiContextFormDataDevLog: Partial<AIContextCreate> = {
    context_data: "{\n  \"detail\": \"value\"\n}",
    notes: "",
    request_id: ""
};

export default function DevLogEntryPage() {
  const router = useRouter();
  const params = useParams();
  const entryIdStr = params.id as string;
  const entryIdNum = parseInt(entryIdStr);

  const [entry, setEntry] = useState<DevLogRead | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState<DevLogUpdate>({});

  const [summary, setSummary] = useState<DevLogShort | null>(null);
  const [viewableAiContexts, setViewableAiContexts] = useState<AIContextRead[] | null>(null);

  const [loading, setLoading] = useState(true);
  const [loadingEdit, setLoadingEdit] = useState(false);
  const [loadingDelete, setLoadingDelete] = useState(false);
  const [loadingRestore, setLoadingRestore] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingViewableAiContext, setLoadingViewableAiContext] = useState(false);

  const [error, setError] = useState<string | null>(null); // General page error
  const [errorEdit, setErrorEdit] = useState<string | null>(null);

  const [managedAiContextsList, setManagedAiContextsList] = useState<AIContextRead[] | null>(null);
  const [loadingManagedAiContextsList, setLoadingManagedAiContextsList] = useState(false);
  const [isAiContextFormOpen, setIsAiContextFormOpen] = useState(false);
  const [editingAiContext, setEditingAiContext] = useState<AIContextRead | null>(null);
  const [aiContextFormData, setAiContextFormData] = useState<Partial<AIContextCreate | AIContextUpdateType>>(initialAiContextFormDataDevLog);
  const [loadingAiContextForm, setLoadingAiContextForm] = useState(false);
  const [errorAiContextForm, setErrorAiContextForm] = useState<string | null>(null);

  const fetchEntryDetails = useCallback(async () => {
    if (!entryIdStr || isNaN(entryIdNum)) {
        const msg = "Invalid Entry ID."; setError(msg); toast.error(msg); setLoading(false); return;
    }
    setLoading(true); setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const data = await getDevlog(entryIdNum, token ?? undefined);
      setEntry(data);
      setEditFormData({ title: data.title, content: data.content, entry_type: data.entry_type, project_id: data.project_id, task_id: data.task_id, tags: data.tags || [] });
    } catch (err: any) {
        const msg = err.message || "Failed to fetch devlog entry.";
        setError(msg); toast.error(msg); setEntry(null);
    }
    finally { setLoading(false); }
  }, [entryIdStr, entryIdNum]);

  const handleFetchViewableAiContext = useCallback(async () => {
    if (!entry || isNaN(entryIdNum)) return;
    setLoadingViewableAiContext(true); // setError(null); // Use general error or a specific one
    const toastId = toast.loading("Fetching linked AI contexts...");
    setViewableAiContexts(null);
    try {
      const token = localStorage.getItem("access_token");
      const data = await getDevlogEntryAIContext(entryIdNum, token ?? undefined);
      setViewableAiContexts(data);
      toast.success("Linked AI contexts loaded.", { id: toastId });
    } catch (err: any) {
        const msg = err.message || "Failed to fetch linked AI contexts.";
        setError(prev => prev ? `${prev}\n${msg}`: msg); // Append to general error or use specific state
        toast.error(msg, { id: toastId });
        setViewableAiContexts([]);
    }
    finally { setLoadingViewableAiContext(false); }
  }, [entry, entryIdNum]);

  const fetchDevlogEntryManagedAiContextsList = useCallback(async () => {
    if (isNaN(entryIdNum)) return;
    setLoadingManagedAiContextsList(true);
    let specificError = null;
    try {
      const token = localStorage.getItem("access_token");
      const contexts = await listAIContexts({ object_type: "devlog_entry", object_id: entryIdNum, limit: 50 }, token ?? undefined);
      setManagedAiContextsList(contexts.sort((a,b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    } catch (err: any) {
        specificError = err.message || "Failed to fetch AI contexts for management.";
        toast.error(specificError);
        setManagedAiContextsList([]);
    } finally {
        setLoadingManagedAiContextsList(false);
        if(specificError && !error) setError(specificError);
    }
  }, [entryIdNum, error]);

  useEffect(() => {
    fetchEntryDetails();
    fetchDevlogEntryManagedAiContextsList();
  }, [fetchEntryDetails, fetchDevlogEntryManagedAiContextsList]);

   useEffect(() => {
    if (entry && !viewableAiContexts && !loadingViewableAiContext) { // Fetch only if entry is loaded and contexts not yet fetched/loading
        handleFetchViewableAiContext();
    }
  }, [entry, viewableAiContexts, loadingViewableAiContext, handleFetchViewableAiContext]);

  const handleEditChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => { const { name, value, type } = e.target; const isNumericField = type === 'number' || name === 'project_id' || name === 'task_id'; setEditFormData(prev => ({ ...prev, [name]: isNumericField && value === '' ? undefined : (isNumericField ? Number(value) : value) })); };
  const handleEditSelectChange = (name: keyof DevLogUpdate, value: string) => setEditFormData(prev => ({ ...prev, [name]: value }));
  const handleEditTagsChange = (e: ChangeEvent<HTMLInputElement>) => setEditFormData(prev => ({ ...prev, tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag) }));

  const handleUpdateSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editFormData.title?.trim()) { toast.error("Title cannot be empty."); setErrorEdit("Title cannot be empty."); return; }
    setLoadingEdit(true); setErrorEdit(null);
    const toastId = toast.loading("Updating entry...");
    try {
      const token = localStorage.getItem("access_token");
      const updated = await updateDevlog(entryIdNum, editFormData, token ?? undefined);
      setEntry(updated); setIsEditing(false);
      toast.success("Entry updated successfully!", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to update entry."; setErrorEdit(msg); toast.error(msg, { id: toastId });}
    finally { setLoadingEdit(false); }
  };
  const handleCancelEdit = () => { setIsEditing(false); setErrorEdit(null); if (entry) setEditFormData({ title: entry.title, content: entry.content, entry_type: entry.entry_type, project_id: entry.project_id, task_id: entry.task_id, tags: entry.tags || [] }); };

  const handleDeleteArchive = async () => {
    if (!entry) return;
    const actionVerb = entry.is_deleted ? 'permanently delete' : 'archive';
    if (window.confirm(`Are you sure you want to ${actionVerb} this entry?`)) {
      setLoadingDelete(true); setError(null);
      const toastId = toast.loading(`${actionVerb.charAt(0).toUpperCase() + actionVerb.slice(1)}ing entry...`);
      try {
        const token = localStorage.getItem("access_token");
        await deleteDevlog(entryIdNum, token ?? undefined);
        toast.success(`Entry ${actionVerb}d successfully.`, { id: toastId });
        router.push("/devlog");
      } catch (err: any) { const msg = err.message || "Failed to delete entry."; setError(msg); toast.error(msg, { id: toastId }); setLoadingDelete(false); }
    }
  };
  const handleRestore = async () => {
    if (!entry || !entry.is_deleted) return;
    setLoadingRestore(true); setError(null);
    const toastId = toast.loading("Restoring entry...");
    try {
      const token = localStorage.getItem("access_token");
      const restored = await restoreDevlog(entryIdNum, token ?? undefined);
      setEntry(restored);
      setEditFormData({ title: restored.title, content: restored.content, entry_type: restored.entry_type, project_id: restored.project_id, task_id: restored.task_id, tags: restored.tags || [] });
      toast.success("Entry restored successfully!", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to restore entry."; setError(msg); toast.error(msg, { id: toastId });}
    finally { setLoadingRestore(false); }
  };
  const handleFetchSummary = async () => {
    if (!entry) return;
    setLoadingSummary(true); setError(null); setSummary(null);
    const toastId = toast.loading("Fetching summary...");
    try {
      const token = localStorage.getItem("access_token");
      const data = await summarizeDevlogEntry(entryIdNum, token ?? undefined);
      setSummary(data);
      toast.success("Summary loaded.", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to fetch summary."; setError(msg); toast.error(msg, { id: toastId });}
    finally { setLoadingSummary(false); }
  };

  const openAiContextFormForNew = () => { setEditingAiContext(null); setAiContextFormData(initialAiContextFormDataDevLog); setErrorAiContextForm(null); setIsAiContextFormOpen(true); };
  const openAiContextFormForEdit = (context: AIContextRead) => { setEditingAiContext(context); setAiContextFormData({ context_data: typeof context.context_data === 'string' ? context.context_data : JSON.stringify(context.context_data, null, 2), notes: context.notes, request_id: context.request_id }); setErrorAiContextForm(null); setIsAiContextFormOpen(true); };
  const handleAiContextFormChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => { const { name, value } = e.target; setAiContextFormData(prev => ({ ...prev, [name]: value })); };

  const handleAiContextFormSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (isNaN(entryIdNum)) { toast.error("DevLog Entry ID is invalid."); setErrorAiContextForm("DevLog Entry ID is invalid."); return; }
    let parsedContextData;
    const contextDataField = (aiContextFormData as AIContextCreate).context_data || (aiContextFormData as AIContextUpdateType).context_data;
    try { if (typeof contextDataField !== 'string') throw new Error("Context data must be stringified JSON."); parsedContextData = JSON.parse(contextDataField); }
    catch (err) { toast.error("Context Data is not valid JSON."); setErrorAiContextForm("Context Data is not valid JSON."); return; }
    setLoadingAiContextForm(true); setErrorAiContextForm(null);
    const toastId = toast.loading("Saving AI context...");
    try {
        const token = localStorage.getItem("access_token");
        if (editingAiContext) {
            await updateAIContext(editingAiContext.id, { context_data: parsedContextData, notes: aiContextFormData.notes }, token ?? undefined);
        } else {
            await createAIContext({ object_type: "devlog_entry", object_id: entryIdNum, context_data: parsedContextData, notes: aiContextFormData.notes, request_id: aiContextFormData.request_id }, token ?? undefined);
        }
        setIsAiContextFormOpen(false); fetchDevlogEntryManagedAiContextsList();
        toast.success("AI Context saved successfully!", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to save AI Context."; setErrorAiContextForm(msg); toast.error(msg, { id: toastId });}
    finally { setLoadingAiContextForm(false); }
  };
  const handleDeleteAiContext = async (contextId: number) => {
    if (!window.confirm("Delete this AI Context?")) return;
    const toastId = toast.loading("Deleting AI context...");
    try {
        const token = localStorage.getItem("access_token");
        await deleteAiContextEntry(contextId, token ?? undefined);
        fetchDevlogEntryManagedAiContextsList();
        toast.success("AI Context deleted.", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to delete AI Context."; setError(msg); toast.error(msg, { id: toastId });} // Use general page error for now
  };

  if (loading) return <div className="flex justify-center items-center min-h-screen"><Loader2 className="w-12 h-12 animate-spin text-purple-500" /></div>;
  if (error && !entry) return <div className="container mx-auto py-10 px-4"><Alert variant="destructive"><AlertCircleIcon className="h-4 w-4" /><AlertTitle>Error Loading DevLog Entry</AlertTitle><AlertDescription>{error}<Button variant="link" onClick={fetchEntryDetails} className="p-0 h-auto ml-2">Retry</Button></AlertDescription></Alert><Button onClick={() => router.push("/devlog")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" /> Back to DevLog List</Button></Alert></div>;
  if (!entry) return <div className="container mx-auto py-10 px-4 text-center"><Alert><AlertCircleIcon className="h-4 w-4" /><AlertTitle>Not Found</AlertTitle><AlertDescription>DevLog entry not found.</AlertDescription></Alert><Button onClick={() => router.push("/devlog")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" /> Back to DevLog List</Button></div>;

  const canManageEntry = true; // Placeholder for actual permission check

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      {error && <Alert variant="destructive" className="mb-4"><AlertCircleIcon className="h-4 w-4"/><AlertTitle>An Error Occurred</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      <div className="flex justify-between items-center mb-6">
        <Button onClick={() => router.push("/devlog")} variant="outline" size="sm" className="dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700"><ArrowLeft className="w-4 h-4 mr-2" /> Back to List</Button>
        {canManageEntry && (<div className="flex space-x-2">
          {!isEditing && !entry.is_deleted && <Button onClick={() => setIsEditing(true)} variant="outline" className="dark:text-gray-300 dark:border-gray-600"><Edit3 className="w-4 h-4 mr-2" />Edit</Button>}
          {!isEditing && entry.is_deleted && <Button onClick={handleRestore} variant="outline" className="text-green-600 border-green-500" disabled={loadingRestore}>{loadingRestore ? <Loader2 className="w-4 h-4 animate-spin mr-2"/> : <ArchiveRestore className="w-4 h-4 mr-2" />}Restore</Button>}
          {!isEditing && <Button onClick={handleDeleteArchive} variant="destructive" disabled={loadingDelete}>{loadingDelete ? <Loader2 className="w-4 h-4 animate-spin mr-2"/> : <Trash2 className="w-4 h-4 mr-2" />}{entry.is_deleted ? "Delete Permanently" : "Archive"}</Button>}
        </div>)}
      </div>

      {entry.is_deleted && !isEditing && <Alert variant="default" className="mb-6 bg-yellow-100 border-yellow-400 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-700"><Info className="h-4 w-4" /><AlertTitle>Archived Entry</AlertTitle><AlertDescription>This entry is archived. {canManageEntry && "You can restore or delete it permanently."}</AlertDescription></Alert>}

      {!isEditing ? ( /* View Mode */ <Card className="mb-8 dark:bg-gray-800 shadow-lg"> {/* ... existing view JSX ... */} </Card>)
      : ( canManageEntry && <Card className="my-8 dark:bg-gray-800 shadow-xl">{/* ... existing edit form JSX ... */}</Card>)}

      {/* Original AI Context Display & Summary (if needed, or remove if new section is sufficient) */}
      {!isEditing && !entry.is_deleted && (
        <div className="my-8 grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="dark:bg-gray-800"><CardHeader className="flex flex-row items-center justify-between pb-2"><CardTitle className="text-lg font-medium dark:text-white">Entry Summary</CardTitle><Button onClick={handleFetchSummary} variant="ghost" size="sm" disabled={loadingSummary} className="dark:text-purple-400">{loadingSummary ? <Loader2 className="w-4 h-4 animate-spin"/> : <Info className="w-4 h-4"/>}</Button></CardHeader>
            <CardContent>{loadingSummary && <div className="flex justify-center p-2"><Loader2 className="w-5 h-5 animate-spin"/></div>}{summary && !loadingSummary && <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-3 rounded-md overflow-x-auto">{JSON.stringify(summary, null, 2)}</pre>}{!summary && !loadingSummary && <p className="text-sm text-gray-500">Click to load summary.</p>}</CardContent>
          </Card>
          <Card className="dark:bg-gray-800"><CardHeader className="flex flex-row items-center justify-between pb-2"><CardTitle className="text-lg font-medium dark:text-white">Linked AI Context (View)</CardTitle><Button onClick={handleFetchViewableAiContext} variant="ghost" size="sm" disabled={loadingViewableAiContext} className="dark:text-purple-400">{loadingViewableAiContext ? <Loader2 className="w-4 h-4 animate-spin"/> : <Brain className="w-4 h-4"/>}</Button></CardHeader>
            <CardContent>{loadingViewableAiContext && <div className="flex justify-center p-2"><Loader2 className="w-5 h-5 animate-spin"/></div>}{viewableAiContexts && !loadingViewableAiContext && <div className="space-y-1 max-h-48 overflow-y-auto">{viewableAiContexts.length > 0 ? viewableAiContexts.map((ctx, i) => <div key={i} className="text-xs bg-gray-100 dark:bg-gray-900 p-2 rounded"><p>ID: {ctx.id}</p><p>Created: {formatDate(ctx.created_at)}</p></div>) : <p className="text-sm text-gray-500">No linked contexts found via this view.</p>}</div>}{!viewableAiContexts && !loadingViewableAiContext && <p className="text-sm text-gray-500">Click to load linked AI contexts.</p>}</CardContent>
          </Card>
        </div>
      )}

      {/* New AI Context Management Section */}
      {!isEditing && !entry.is_deleted && (
        <Card className="mt-8 dark:bg-gray-800 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between pb-3 border-b dark:border-gray-700">
              <CardTitle className="text-xl font-semibold dark:text-white flex items-center"><Brain className="w-5 h-5 mr-2 text-sky-400"/>Manage AI Contexts</CardTitle>
              <Button size="sm" onClick={openAiContextFormForNew} className="bg-sky-500 hover:bg-sky-600 text-white text-xs"><PlusSquare className="w-4 h-4 mr-1.5"/>Create Context</Button>
            </CardHeader>
            <CardContent className="pt-4">
              {loadingManagedAiContextsList && <div className="flex justify-center p-3"><Loader2 className="animate-spin w-6 h-6 text-sky-500"/></div>}
              {error && !loadingManagedAiContextsList && managedAiContextsList === null && <Alert variant="destructive" className="text-xs"><AlertCircleIcon className="h-4 w-4"/><AlertDescription>{error.includes("AI context") ? error : "Could not load AI Contexts."}</AlertDescription></Alert>}
              {managedAiContextsList && !loadingManagedAiContextsList && (
                <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
                  {managedAiContextsList.length > 0 ? managedAiContextsList.map((ctx) => (
                    <Card key={ctx.id} className="text-xs bg-gray-50 dark:bg-gray-900 p-3 rounded-md">
                      <CardContent className="p-0 space-y-1.5">
                        <div className="flex justify-between items-start mb-1.5">
                            <div><p className="font-medium text-gray-700 dark:text-gray-200">ID: {ctx.id} {ctx.request_id && `(Req: ${ctx.request_id})`}</p></div>
                            <div className="space-x-0.5 flex-shrink-0">
                                <Button variant="ghost" size="icon" className="h-6 w-6 dark:text-gray-400 hover:dark:text-blue-400" onClick={() => openAiContextFormForEdit(ctx)}><Edit3 className="w-3.5 h-3.5"/></Button>
                                <Button variant="ghost" size="icon" className="h-6 w-6 dark:text-gray-400 hover:dark:text-red-400" onClick={() => handleDeleteAiContext(ctx.id)}><Trash2 className="w-3.5 h-3.5"/></Button>
                            </div>
                        </div>
                        <details className="text-gray-600 dark:text-gray-300"><summary className="cursor-pointer text-xs hover:underline">View Data</summary><pre className="mt-1 text-xs whitespace-pre-wrap overflow-x-auto bg-gray-100 dark:bg-gray-800 p-2 rounded max-h-32">{typeof ctx.context_data === 'string' ? ctx.context_data : JSON.stringify(ctx.context_data, null, 2)}</pre></details>
                        {ctx.notes && <p className="mt-1 pt-1 border-t dark:border-gray-700 text-gray-600 dark:text-gray-300"><strong>Notes:</strong> {ctx.notes}</p>}
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Created: {formatDate(ctx.created_at)} by {ctx.created_by}</p>
                      </CardContent>
                    </Card>
                  )) : <p className="text-sm text-center text-gray-500 dark:text-gray-400 py-4">No AI contexts for this entry.</p>}
                </div>
              )}
              {(!managedAiContextsList && !loadingManagedAiContextsList && !error) && <p className="text-sm text-gray-500 dark:text-gray-400">Click the <Brain className="inline w-4 h-4"/> icon to load contexts (if available).</p>}
            </CardContent>
        </Card>
      )}

      <Dialog open={isAiContextFormOpen} onOpenChange={setIsAiContextFormOpen}>
        <DialogContent className="dark:bg-gray-800 sm:max-w-lg">
          <DialogHeader><DialogTitle className="dark:text-white">{editingAiContext ? "Edit AI Context" : "Create AI Context for DevLog Entry"}</DialogTitle><DialogDescription className="dark:text-gray-400">{editingAiContext ? "Modify details." : "Add new AI context."}</DialogDescription></DialogHeader>
          {errorAiContextForm && <Alert variant="destructive" className="my-2"><AlertCircleIcon className="h-4 w-4"/><AlertDescription>{errorAiContextForm}</AlertDescription></Alert>}
          <form onSubmit={handleAiContextFormSubmit} className="space-y-4 pt-2">
            <div><Label htmlFor="ai-ctx-data" className="dark:text-gray-300">Context Data (JSON) <span className="text-red-500">*</span></Label><Textarea id="ai-ctx-data" name="context_data" value={(aiContextFormData as any).context_data || ""} onChange={handleAiContextFormChange} rows={7} placeholder='Enter valid JSON...' required className="font-mono text-xs dark:bg-gray-700 dark:border-gray-600" disabled={loadingAiContextForm} /></div>
            <div><Label htmlFor="ai-ctx-notes" className="dark:text-gray-300">Notes</Label><Input id="ai-ctx-notes" name="notes" value={aiContextFormData.notes || ""} onChange={handleAiContextFormChange} placeholder="Optional notes" className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingAiContextForm} /></div>
            {!editingAiContext && (<div><Label htmlFor="ai-ctx-reqid" className="dark:text-gray-300">Request ID</Label><Input id="ai-ctx-reqid" name="request_id" value={aiContextFormData.request_id || ""} onChange={handleAiContextFormChange} placeholder="Optional request ID" className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingAiContextForm} /></div>)}
            <DialogFooter className="pt-3"><DialogClose asChild><Button type="button" variant="outline" className="dark:text-gray-300 dark:border-gray-600" disabled={loadingAiContextForm}>Cancel</Button></DialogClose><Button type="submit" className="bg-sky-500 hover:bg-sky-600 text-white" disabled={loadingAiContextForm}>{loadingAiContextForm ? <Loader2 className="mr-2 h-4 w-4 animate-spin"/> : <Save className="w-4 h-4 mr-2" />}{editingAiContext ? "Save" : "Create"}</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
