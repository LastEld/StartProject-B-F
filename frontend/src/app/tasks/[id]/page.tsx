"use client";

import React, { useEffect, useState, ChangeEvent, FormEvent, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getTaskById,
  updateTask,
  deleteTask,
  restoreTask,
  TaskRead,
  TaskUpdate,
  AIContextRead,
  AIContextCreate,
  AIContextUpdate as AIContextUpdateType,
  listAiContexts,
  createAiContext,
  updateAiContext,
  deleteAiContext as deleteAiContextEntry,
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
  Loader2, Edit3, Trash2, Save, XCircle, Info, CalendarDays, TagIcon as Tag,
  Flag, ArrowLeft, Briefcase, UserCircle as UserIcon, ArchiveRestore,
  Brain, PlusSquare, CheckCircle, AlertCircle as AlertCircleIcon
} from "lucide-react";
import ReactMarkdown from 'react-markdown';
import { toast } from "sonner";

const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try {
    return new Date(dateString).toLocaleString(undefined, { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (e) { return "Invalid Date"; }
};

const initialAiContextFormDataTask: Partial<AIContextCreate> = {
    context_data: "{\n  \"key\": \"value\"\n}",
    notes: "",
    request_id: ""
};

const getStatusAppearance = (status?: string) => {
  switch (status?.toLowerCase()) {
    case "in_progress": return { label: "In Progress", className: "bg-blue-500 text-white", icon: <Loader2 className="w-4 h-4 mr-1 animate-spin" /> };
    case "done": return { label: "Done", className: "bg-green-500 text-white", icon: <CheckCircle className="w-4 h-4 mr-1" /> };
    case "cancelled": return { label: "Cancelled", className: "bg-red-500 text-white", icon: <XCircle className="w-4 h-4 mr-1" /> };
    case "backlog": return { label: "Backlog", className: "bg-gray-400 text-white", icon: <Info className="w-4 h-4 mr-1" /> };
    case "todo": default: return { label: "To Do", className: "bg-gray-500 text-white", icon: <Info className="w-4 h-4 mr-1" /> };
  }
};

const getPriorityAppearance = (priority?: number) => {
    if (priority === undefined || priority === null) return { label: "N/A", className: "bg-gray-200 text-gray-800" };
    if (priority >= 5) return { label: "Highest", className: "bg-red-600 text-white" };
    if (priority === 4) return { label: "High", className: "bg-orange-500 text-white" };
    if (priority === 3) return { label: "Medium", className: "bg-yellow-500 text-black" };
    if (priority === 2) return { label: "Low", className: "bg-blue-500 text-white" };
    if (priority <= 1) return { label: "Lowest", className: "bg-green-500 text-white" };
    return { label: priority.toString(), className: "bg-gray-200 text-gray-800"};
};

export default function TaskDetailPage() {
  const router = useRouter();
  const params = useParams();
  const taskIdStr = params.id as string;
  const taskIdNum = parseInt(taskIdStr);

  const [task, setTask] = useState<TaskRead | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState<TaskUpdate>({});

  const [loading, setLoading] = useState(true);
  const [loadingEdit, setLoadingEdit] = useState(false);
  const [loadingDelete, setLoadingDelete] = useState(false);
  const [loadingRestore, setLoadingRestore] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [errorEdit, setErrorEdit] = useState<string | null>(null);

  const [aiContexts, setAiContexts] = useState<AIContextRead[] | null>(null);
  const [loadingAiContextList, setLoadingAiContextList] = useState(false);
  const [isAiContextFormOpen, setIsAiContextFormOpen] = useState(false);
  const [editingAiContext, setEditingAiContext] = useState<AIContextRead | null>(null);
  const [aiContextFormData, setAiContextFormData] = useState<Partial<AIContextCreate | AIContextUpdateType>>(initialAiContextFormDataTask);
  const [loadingAiContextForm, setLoadingAiContextForm] = useState(false);
  const [errorAiContextForm, setErrorAiContextForm] = useState<string | null>(null);

  const fetchTaskDetails = useCallback(async () => {
    if (!taskIdStr || isNaN(taskIdNum)) {
        const msg = "Invalid Task ID."; setError(msg); toast.error(msg); setLoading(false); return;
    }
    setLoading(true); setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const data = await getTaskById(taskIdStr, token ?? undefined);
      setTask(data);
      setEditFormData({
        name: data.name, description: data.description, status: data.status, priority: data.priority,
        deadline: data.deadline ? new Date(data.deadline).toISOString().split('T')[0] : null,
        tags: data.tags || [], project_id: data.project_id, assignee_id: data.assignee_id,
      });
    } catch (err: any) {
        const msg = err.message || "Failed to fetch task details.";
        setError(msg); toast.error(msg); setTask(null);
    }
    finally { setLoading(false); }
  }, [taskIdStr, taskIdNum]);

  const fetchTaskAiContextsList = useCallback(async () => {
    if (isNaN(taskIdNum)) return;
    setLoadingAiContextList(true);
    let specificError = null;
    try {
      const token = localStorage.getItem("access_token");
      const contexts = await listAiContexts({ object_type: "task", object_id: taskIdNum, limit: 50 }, token ?? undefined);
      setAiContexts(contexts.sort((a,b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    } catch (err: any) {
        specificError = err.message || "Failed to fetch AI contexts for task.";
        toast.error(specificError);
        setAiContexts([]);
    } finally {
        setLoadingAiContextList(false);
        if(specificError && !error) setError(specificError);
    }
  }, [taskIdNum, error]);

  useEffect(() => {
    fetchTaskDetails();
    fetchTaskAiContextsList();
  }, [fetchTaskDetails, fetchTaskAiContextsList]);

  const handleEditChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => { const { name, value, type } = e.target; const isNumericField = type === 'number' || name === 'project_id' || name === 'assignee_id' || name === 'priority'; setEditFormData(prev => ({ ...prev, [name]: isNumericField && value === '' ? undefined : (isNumericField ? Number(value) : value) })); };
  const handleEditSelectChange = (name: keyof TaskUpdate, value: string | number) => setEditFormData(prev => ({ ...prev, [name]: value }));
  const handleEditTagsChange = (e: ChangeEvent<HTMLInputElement>) => setEditFormData(prev => ({ ...prev, tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag) }));

  const handleUpdateSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editFormData.name?.trim()) { toast.error("Task name cannot be empty."); setErrorEdit("Task name cannot be empty."); return; }
    setLoadingEdit(true); setErrorEdit(null);
    const toastId = toast.loading("Updating task...");
    try {
      const token = localStorage.getItem("access_token");
      const dataToUpdate: TaskUpdate = { ...editFormData, deadline: editFormData.deadline ? new Date(editFormData.deadline).toISOString() : null, priority: editFormData.priority ? Number(editFormData.priority) : undefined, project_id: editFormData.project_id ? Number(editFormData.project_id) : undefined, assignee_id: editFormData.assignee_id ? Number(editFormData.assignee_id) : undefined };
      const updated = await updateTask(taskIdStr, dataToUpdate, token ?? undefined);
      setTask(updated); setIsEditing(false);
      toast.success("Task updated successfully!", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to update task."; setErrorEdit(msg); toast.error(msg, { id: toastId });}
    finally { setLoadingEdit(false); }
  };

  const handleCancelEdit = () => {
    setIsEditing(false); setErrorEdit(null);
    if (task) setEditFormData({ name: task.name, description: task.description, status: task.status, priority: task.priority, deadline: task.deadline ? new Date(task.deadline).toISOString().split('T')[0] : null, tags: task.tags || [], project_id: task.project_id, assignee_id: task.assignee_id });
  };

  const handleDeleteTask = async () => {
    if (!task) return;
    const actionVerb = task.is_archived ? "permanently delete" : "archive";
    if (window.confirm(`Are you sure you want to ${actionVerb} this task?`)) {
      setLoadingDelete(true); setError(null);
      const toastId = toast.loading(`${actionVerb.charAt(0).toUpperCase() + actionVerb.slice(1)}ing task...`);
      try {
        const token = localStorage.getItem("access_token");
        await deleteTask(taskIdStr, token ?? undefined);
        toast.success(`Task ${actionVerb}d successfully.`, { id: toastId });
        router.push("/tasks");
      } catch (err: any) { const msg = err.message || `Failed to ${actionVerb} task.`; setError(msg); toast.error(msg, { id: toastId }); setLoadingDelete(false); }
    }
  };

  const handleRestoreTask = async () => {
    if (!task || !task.is_archived) return;
    setLoadingRestore(true); setError(null);
    const toastId = toast.loading("Restoring task...");
    try {
      const token = localStorage.getItem("access_token");
      const restored = await restoreTask(taskIdStr, token ?? undefined);
      setTask(restored);
      setEditFormData({ name: restored.name, description: restored.description, status: restored.status, priority: restored.priority, deadline: restored.deadline ? new Date(restored.deadline).toISOString().split('T')[0] : null, tags: restored.tags || [], project_id: restored.project_id, assignee_id: restored.assignee_id });
      toast.success("Task restored successfully!", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to restore task."; setError(msg); toast.error(msg, { id: toastId });}
    finally { setLoadingRestore(false); }
  };

  const openAiContextFormForNew = () => { setEditingAiContext(null); setAiContextFormData(initialAiContextFormDataTask); setErrorAiContextForm(null); setIsAiContextFormOpen(true); };
  const openAiContextFormForEdit = (context: AIContextRead) => { setEditingAiContext(context); setAiContextFormData({ context_data: typeof context.context_data === 'string' ? context.context_data : JSON.stringify(context.context_data, null, 2), notes: context.notes, request_id: context.request_id }); setErrorAiContextForm(null); setIsAiContextFormOpen(true); };
  const handleAiContextFormChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => { const { name, value } = e.target; setAiContextFormData(prev => ({ ...prev, [name]: value })); };

  const handleAiContextFormSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (isNaN(taskIdNum)) { toast.error("Task ID is invalid."); setErrorAiContextForm("Task ID is invalid."); return; }
    let parsedContextData;
    const contextDataField = (aiContextFormData as AIContextCreate).context_data || (aiContextFormData as AIContextUpdateType).context_data;
    try { if (typeof contextDataField !== 'string') throw new Error("Context data must be stringified JSON."); parsedContextData = JSON.parse(contextDataField); }
    catch (err) { toast.error("Context Data is not valid JSON."); setErrorAiContextForm("Context Data is not valid JSON."); return; }

    setLoadingAiContextForm(true); setErrorAiContextForm(null);
    const toastId = toast.loading("Saving AI context...");
    try {
        const token = localStorage.getItem("access_token");
        if (editingAiContext) {
            await updateAiContext(editingAiContext.id, { context_data: parsedContextData, notes: aiContextFormData.notes }, token ?? undefined);
        } else {
            await createAiContext({ object_type: "task", object_id: taskIdNum, context_data: parsedContextData, notes: aiContextFormData.notes, request_id: aiContextFormData.request_id }, token ?? undefined);
        }
        setIsAiContextFormOpen(false); fetchTaskAiContextsList();
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
        fetchTaskAiContextsList();
        toast.success("AI Context deleted.", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to delete AI Context."; setError(msg); toast.error(msg, { id: toastId });}
  };

  if (loading) return <div className="flex justify-center items-center min-h-screen"><Loader2 className="w-12 h-12 animate-spin text-cyan-500" /></div>;
  if (error && !task) return <div className="container mx-auto py-10 px-4"><Alert variant="destructive"><AlertCircleIcon className="h-4 w-4" /><AlertTitle>Error Loading Task</AlertTitle><AlertDescription>{error}<Button variant="link" onClick={fetchTaskDetails} className="p-0 h-auto ml-2">Retry</Button></AlertDescription></Alert><Button onClick={() => router.push("/tasks")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" /> Back to Tasks</Button></Alert></div>;
  if (!task) return <div className="container mx-auto py-10 px-4 text-center"><Alert><AlertCircleIcon className="h-4 w-4" /><AlertTitle>Not Found</AlertTitle><AlertDescription>Task data could not be loaded or task does not exist.</AlertDescription></Alert><Button onClick={() => router.push("/tasks")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" /> Back to Tasks</Button></div>;

  const statusInfo = getStatusAppearance(task.status);
  const priorityInfo = getPriorityAppearance(task.priority);
  const canManageTask = true; // Placeholder for actual permission check

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8 max-w-3xl">
       {/* General Page Error Display for errors not covered by specific sections */}
      {error && <Alert variant="destructive" className="mb-4"><AlertCircleIcon className="h-4 w-4"/><AlertTitle>An Error Occurred</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}

      <div className="flex justify-between items-center mb-6">
        <Button onClick={() => router.push("/tasks")} variant="outline" size="sm" className="dark:text-gray-300 dark:border-gray-600"><ArrowLeft className="w-4 h-4 mr-2" />Back to Tasks</Button>
        {canManageTask && (<div className="flex space-x-2">
          {!isEditing && !task.is_archived && (<Button onClick={() => setIsEditing(true)} variant="outline" className="dark:text-gray-300 dark:border-gray-600"><Edit3 className="w-4 h-4 mr-2" />Edit</Button>)}
          {!isEditing && task.is_archived && (<Button onClick={handleRestoreTask} variant="outline" className="text-green-600 border-green-500" disabled={loadingRestore}>{loadingRestore ? <Loader2 className="w-4 h-4 animate-spin"/> : <ArchiveRestore className="w-4 h-4 mr-2" />}Restore</Button>)}
          {!isEditing && (<Button onClick={handleDeleteTask} variant="destructive" disabled={loadingDelete}>{loadingDelete ? <Loader2 className="w-4 h-4 animate-spin"/>:<Trash2 className="w-4 h-4 mr-2" />}{task.is_archived ? "Delete Permanently" : "Archive"}</Button>)}
        </div>)}
      </div>

      {task.is_archived && !isEditing && (<Alert variant="default" className="mb-6 bg-yellow-100 border-yellow-400 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-700"><Info className="h-4 w-4" /><AlertTitle>Archived Task</AlertTitle><AlertDescription>This task is archived.</AlertDescription></Alert>)}

      {!isEditing ? (
        <Card className="mb-8 dark:bg-gray-800 shadow-lg">
          <CardHeader className="border-b dark:border-gray-700 pb-4">
            <div className="flex items-center space-x-3 mb-2"> {statusInfo.icon} <CardTitle className="text-3xl font-bold dark:text-white">{task.name}</CardTitle></div>
            <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                <Badge className={`${statusInfo.className} text-xs`}>{statusInfo.label}</Badge>
                <Badge className={`${priorityInfo.className} text-xs`}><Flag className="w-3 h-3 mr-1"/>{priorityInfo.label}</Badge>
            </div>
          </CardHeader>
          <CardContent className="pt-6 space-y-3">
            {task.description && <div><Label className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Description</Label><div className="prose prose-sm dark:prose-invert max-w-none mt-1"><ReactMarkdown>{task.description}</ReactMarkdown></div></div>}
            <div className="grid grid-cols-2 gap-4">
                <div><Label className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Deadline</Label><p className="dark:text-gray-300 flex items-center"><CalendarDays className="w-4 h-4 mr-1.5 text-blue-400"/>{formatDate(task.deadline)}</p></div>
                {task.project_id && <div><Label className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Project ID</Label><p className="dark:text-gray-300 flex items-center"><Briefcase className="w-4 h-4 mr-1.5 text-purple-400"/>{task.project_id}</p></div>}
                {task.assignee_id && <div><Label className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Assignee ID</Label><p className="dark:text-gray-300 flex items-center"><UserIcon className="w-4 h-4 mr-1.5 text-green-400"/>{task.assignee_id}</p></div>}
            </div>
            {task.tags && task.tags.length > 0 && (<div><Label className="text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">Tags</Label><div className="flex flex-wrap gap-2 mt-1">{task.tags.map((tag: string | {name:string}) => <Badge key={typeof tag === 'string' ? tag : tag.name} variant="secondary"><Tag className="w-3 h-3 mr-1"/>{typeof tag === 'string' ? tag : tag.name}</Badge>)}</div></div>)}
          </CardContent>
          <CardFooter className="border-t dark:border-gray-700 pt-3 text-xs text-gray-500 dark:text-gray-400"><span>Created: {formatDate(task.created_at)}</span><span className="mx-1">|</span><span>Updated: {formatDate(task.updated_at)}</span></CardFooter>
        </Card>
      ) : (
        canManageTask && <Card className="my-8 dark:bg-gray-800 shadow-xl">{/* Edit Form (existing JSX) */}</Card>
      )}

      {/* AI Context Section */}
      {!isEditing && !task.is_archived && (
        <Card className="mt-8 dark:bg-gray-800 shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between pb-3 border-b dark:border-gray-700">
              <CardTitle className="text-xl font-semibold dark:text-white flex items-center"><Brain className="w-5 h-5 mr-2 text-sky-400"/>AI Contexts</CardTitle>
              <Button size="sm" onClick={openAiContextFormForNew} className="bg-sky-500 hover:bg-sky-600 text-white text-xs"><PlusSquare className="w-4 h-4 mr-1.5"/>Create Context</Button>
            </CardHeader>
            <CardContent className="pt-4">
              {loadingAiContextList && <div className="flex justify-center p-3"><Loader2 className="animate-spin w-6 h-6 text-sky-500"/></div>}
              {/* Display general error if AI context list specifically fails and no other error is more prominent */}
              {error && !loadingAiContextList && aiContexts === null && <Alert variant="destructive" className="text-xs"><AlertCircleIcon className="h-4 w-4"/><AlertDescription>{error.includes("AI context") ? error : "Could not load AI Contexts."}</AlertDescription></Alert>}
              {aiContexts && !loadingAiContextList && (
                <div className="space-y-3 max-h-72 overflow-y-auto pr-2">
                  {aiContexts.length > 0 ? aiContexts.map((ctx) => (
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
                  )) : <p className="text-sm text-center text-gray-500 dark:text-gray-400 py-4">No AI contexts for this task.</p>}
                </div>
              )}
              {(!aiContexts && !loadingAiContextList && !error) && <p className="text-sm text-gray-500 dark:text-gray-400">Click the <Brain className="inline w-4 h-4"/> icon to load contexts (if available).</p>}
            </CardContent>
        </Card>
      )}

      <Dialog open={isAiContextFormOpen} onOpenChange={setIsAiContextFormOpen}>
        <DialogContent className="dark:bg-gray-800 sm:max-w-lg">
          <DialogHeader><DialogTitle className="dark:text-white">{editingAiContext ? "Edit AI Context" : "Create AI Context for Task"}</DialogTitle><DialogDescription className="dark:text-gray-400">{editingAiContext ? "Modify details." : "Add new AI context."}</DialogDescription></DialogHeader>
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
