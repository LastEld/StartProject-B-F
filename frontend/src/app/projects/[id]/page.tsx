"use client";

import React, { useEffect, useState, ChangeEvent, FormEvent, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getProjectById,
  updateProject,
  deleteProject,
  getProjectSummary,
  ProjectRead,
  ProjectUpdate,
  ProjectSummary,
  AIContextRead,
  AIContextCreate,
  AIContextUpdate as AIContextUpdateType,
  getJarvisHistory,
  postJarvisMessage,
  deleteJarvisHistory,
  ChatMessageRead,
  ChatMessageCreate,
  createAiContext,
  updateAiContext,
  deleteAiContext as deleteAiContextEntry,
  listAiContexts
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
  Loader2, Edit3, Trash2, Save, XCircle, Info, Brain, CalendarDays, TagIcon, Flag, ArrowLeft,
  MessageSquare, Send, PlusSquare, Star, AlertCircle as AlertCircleIcon // Explicitly import AlertCircleIcon
} from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import ReactMarkdown from 'react-markdown';


const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try {
    return new Date(dateString).toLocaleString(undefined, { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return "Invalid Date";
  }
};

const initialAiContextFormData: Partial<AIContextCreate> = {
    context_data: "{\n  \"key\": \"value\"\n}",
    notes: "",
    request_id: ""
};


export default function ProjectDetailPage() {
  const router = useRouter();
  const params = useParams();
  const projectIdStr = params.id as string;
  const projectIdNum = parseInt(projectIdStr);

  const [project, setProject] = useState<ProjectRead | null>(null);
  const [projectSummary, setProjectSummary] = useState<ProjectSummary | null>(null);
  const [aiContexts, setAiContexts] = useState<AIContextRead[] | null>(null); // For the managed list

  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState<ProjectUpdate>({});

  const [loading, setLoading] = useState(true); // Main page load
  const [loadingEdit, setLoadingEdit] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingAiContextList, setLoadingAiContextList] = useState(false);
  const [loadingDelete, setLoadingDelete] = useState(false);

  const [error, setError] = useState<string | null>(null); // General page/fetch error
  const [errorEdit, setErrorEdit] = useState<string | null>(null);

  const [chatMessages, setChatMessages] = useState<ChatMessageRead[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [loadingChat, setLoadingChat] = useState(false);
  const [errorChat, setErrorChat] = useState<string | null>(null);
  const [loadingSendMessage, setLoadingSendMessage] = useState(false);

  const [isAiContextFormOpen, setIsAiContextFormOpen] = useState(false);
  const [editingAiContext, setEditingAiContext] = useState<AIContextRead | null>(null);
  const [aiContextFormData, setAiContextFormData] = useState<Partial<AIContextCreate | AIContextUpdateType>>(initialAiContextFormData);
  const [loadingAiContextForm, setLoadingAiContextForm] = useState(false);
  const [errorAiContextForm, setErrorAiContextForm] = useState<string | null>(null);

  const fetchProjectDetails = useCallback(async () => {
    if (!projectIdStr || isNaN(projectIdNum) ) {
        const msg = "Invalid Project ID.";
        setError(msg);
        toast.error(msg);
        setLoading(false);
        return;
    }
    setLoading(true); setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const data = await getProjectById(projectIdStr, token ?? undefined);
      setProject(data);
      setEditFormData({
        name: data.name, description: data.description, status: data.status, priority: data.priority,
        deadline: data.deadline ? new Date(data.deadline).toISOString().split('T')[0] : null,
        tags: data.tags || [],
      });
    } catch (err: any) {
        const msg = err.message || "Failed to fetch project details.";
        setError(msg);
        toast.error(msg); // Toast for initial load error
        setProject(null);
    }
    finally { setLoading(false); }
  }, [projectIdStr, projectIdNum]);

  const fetchChatHistory = useCallback(async () => {
    if (isNaN(projectIdNum)) return;
    setLoadingChat(true); setErrorChat(null);
    try {
      const token = localStorage.getItem("access_token");
      const history = await getJarvisHistory(projectIdNum, { limit: 100 }, token ?? undefined);
      setChatMessages(history.sort((a,b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()));
    } catch (err: any) { setErrorChat(err.message || "Failed to fetch chat history."); /* Inline error is fine here */ }
    finally { setLoadingChat(false); }
  }, [projectIdNum]);

  const fetchProjectAiContextsList = useCallback(async () => {
    if (isNaN(projectIdNum)) return;
    setLoadingAiContextList(true);
    let specificError = null;
    try {
      const token = localStorage.getItem("access_token");
      const contexts = await listAiContexts({ object_type: "project", object_id: projectIdNum, limit: 50 }, token ?? undefined);
      setAiContexts(contexts.sort((a,b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    } catch (err: any) {
        specificError = err.message || "Failed to fetch AI contexts for project.";
        // toast.error(specificError); // Toasting here might be too much if page already has general error
        setAiContexts([]);
    } finally {
        setLoadingAiContextList(false);
        if(specificError && !error) setError(specificError); // Show general error if no main page error shown yet
    }
  }, [projectIdNum, error]); // Added error to dependency to avoid potential loop if it sets error

  useEffect(() => {
    fetchProjectDetails();
    fetchChatHistory();
    fetchProjectAiContextsList();
  }, [fetchProjectDetails, fetchChatHistory, fetchProjectAiContextsList]);

  const handleEditChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setEditFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  const handleEditSelectChange = (name: keyof ProjectUpdate, value: string | number) => setEditFormData(prev => ({ ...prev, [name]: value }));
  const handleTagChangeEdit = (e: ChangeEvent<HTMLInputElement>) => setEditFormData(prev => ({ ...prev, tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag) }));

  const handleUpdateSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editFormData.name?.trim()) { toast.error("Project name cannot be empty."); setErrorEdit("Project name cannot be empty."); return; }
    setLoadingEdit(true); setErrorEdit(null);
    const toastId = toast.loading("Updating project...");
    try {
      const token = localStorage.getItem("access_token");
      const dataToUpdate = { ...editFormData, deadline: editFormData.deadline ? new Date(editFormData.deadline).toISOString() : null, priority: editFormData.priority ? Number(editFormData.priority) : null };
      const updated = await updateProject(projectIdStr, dataToUpdate, token ?? undefined);
      setProject(updated); setIsEditing(false);
      toast.success("Project updated successfully!", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to update project."; setErrorEdit(msg); toast.error(msg, { id: toastId });}
    finally { setLoadingEdit(false); }
  };

  const handleCancelEdit = () => {
    setIsEditing(false); setErrorEdit(null);
    if (project) setEditFormData({ name: project.name, description: project.description, status: project.status, priority: project.priority, deadline: project.deadline ? new Date(project.deadline).toISOString().split('T')[0] : null, tags: project.tags || [] });
  };

  const handleDeleteProject = async () => {
    if (!project) return;
    if (window.confirm("Are you sure you want to archive this project?")) {
      setLoadingDelete(true); setError(null);
      const toastId = toast.loading("Archiving project...");
      try {
        const token = localStorage.getItem("access_token");
        await deleteProject(projectIdStr, token ?? undefined);
        toast.success("Project archived.", { id: toastId });
        await fetchProjectDetails();
      } catch (err: any) { const msg = err.message || "Failed to archive project."; setError(msg); toast.error(msg, { id: toastId });}
      finally { setLoadingDelete(false); }
    }
  };

  const handleFetchSummary = async () => {
    if (!project) return;
    setLoadingSummary(true); setError(null); setProjectSummary(null);
    const toastId = toast.loading("Fetching project summary...");
    try {
      const token = localStorage.getItem("access_token");
      const summary = await getProjectSummary(projectIdStr, token ?? undefined);
      setProjectSummary(summary);
      toast.success("Summary loaded.", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to fetch project summary."; /*setError(msg);*/ toast.error(msg, { id: toastId }); setProjectSummary(null); } // Error displayed inline for this section is fine
    finally { setLoadingSummary(false); }
  };

  const handleSendMessage = async (e: FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || isNaN(projectIdNum)) return;
    setLoadingSendMessage(true); setErrorChat(null);
    try {
      const token = localStorage.getItem("access_token");
      const messageData: ChatMessageCreate = { project_id: projectIdNum, content: newMessage, role: "user" };
      await postJarvisMessage(messageData, token ?? undefined);
      fetchChatHistory(); setNewMessage("");
      // toast.success("Message sent!"); // Usually too noisy for chat
    } catch (err: any) { const msg = err.message || "Failed to send message."; setErrorChat(msg); toast.error(msg); }
    finally { setLoadingSendMessage(false); }
  };

  const handleDeleteChatHistory = async () => {
    if (isNaN(projectIdNum) || !window.confirm("Are you sure you want to delete the entire chat history for this project?")) return;
    setErrorChat(null);
    const toastId = toast.loading("Deleting chat history...");
    try {
      const token = localStorage.getItem("access_token");
      await deleteJarvisHistory(projectIdNum, token ?? undefined);
      setChatMessages([]);
      toast.success("Chat history deleted.", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to delete chat history."; setErrorChat(msg); toast.error(msg, { id: toastId });}
  };

  const openAiContextFormForNew = () => { setEditingAiContext(null); setAiContextFormData(initialAiContextFormData); setErrorAiContextForm(null); setIsAiContextFormOpen(true); };
  const openAiContextFormForEdit = (context: AIContextRead) => { setEditingAiContext(context); setAiContextFormData({ context_data: typeof context.context_data === 'string' ? context.context_data : JSON.stringify(context.context_data, null, 2), notes: context.notes, request_id: context.request_id }); setErrorAiContextForm(null); setIsAiContextFormOpen(true); };
  const handleAiContextFormChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => { const { name, value } = e.target; setAiContextFormData(prev => ({ ...prev, [name]: value })); };

  const handleAiContextFormSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (isNaN(projectIdNum)) { toast.error("Project ID is invalid."); setErrorAiContextForm("Project ID is invalid."); return; }
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
            await createAiContext({ object_type: "project", object_id: projectIdNum, context_data: parsedContextData, notes: aiContextFormData.notes, request_id: aiContextFormData.request_id }, token ?? undefined);
        }
        setIsAiContextFormOpen(false); fetchProjectAiContextsList();
        toast.success("AI Context saved successfully!", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to save AI Context."; setErrorAiContextForm(msg); toast.error(msg, { id: toastId });}
    finally { setLoadingAiContextForm(false); }
  };

  const handleDeleteAiContext = async (contextId: number) => {
    if (!window.confirm("Delete this AI Context?")) return;
    const toastId = toast.loading("Deleting AI context...");
    // setError(null); // Use specific error for this action if needed, or general page error
    try {
        const token = localStorage.getItem("access_token");
        await deleteAiContextEntry(contextId, token ?? undefined);
        fetchProjectAiContextsList();
        toast.success("AI Context deleted.", { id: toastId });
    } catch (err: any) { const msg = err.message || "Failed to delete AI Context."; setError(msg); toast.error(msg, { id: toastId });}
  };

  if (loading) return <div className="flex justify-center items-center min-h-screen"><Loader2 className="w-12 h-12 animate-spin text-blue-500" /></div>;
  if (error && !project) return <div className="container mx-auto py-10 px-4"><Alert variant="destructive"><AlertCircleIcon className="h-4 w-4" /><AlertTitle>Error Loading Project</AlertTitle><AlertDescription>{error}<Button variant="link" onClick={fetchProjectDetails} className="p-0 h-auto ml-2">Retry</Button></AlertDescription></Alert><Button onClick={() => router.push("/projects")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" /> Back to Projects</Button></Alert></div>;
  if (!project) return <div className="container mx-auto py-10 px-4 text-center"><Alert><AlertCircleIcon className="h-4 w-4"/><AlertTitle>Not Found</AlertTitle><AlertDescription>Project data could not be loaded or project does not exist.</AlertDescription></Alert><Button onClick={() => router.push("/projects")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" /> Back to Projects</Button></div>;

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      {/* General Page Error Display (e.g., for AI context list load error if not handled inline) */}
      {error && <Alert variant="destructive" className="mb-4"><AlertCircleIcon className="h-4 w-4"/><AlertTitle>An Error Occurred</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}

      {/* Project Details and Edit Form (existing code) */}
      <div className="flex justify-between items-center mb-6">
        <Button onClick={() => router.push("/projects")} variant="outline" size="sm" className="dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Projects
        </Button>
        <div className="flex space-x-2">
          {!isEditing && project && !project.is_archived && (
            <>
              <Button onClick={() => setIsEditing(true)} variant="outline" className="dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700">
                <Edit3 className="w-4 h-4 mr-2" /> Edit
              </Button>
              <Button onClick={handleDeleteProject} variant="destructive" disabled={loadingDelete}>
                {loadingDelete ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Trash2 className="w-4 h-4 mr-2" />}
                Archive
              </Button>
            </>
          )}
           {!isEditing && project && project.is_archived && (
             <Alert variant="default" className="bg-yellow-100 border-yellow-400 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-700">
                <Info className="h-4 w-4" />
                <AlertDescription>
                  This project is archived. To unarchive, please use the main projects list if available.
                </AlertDescription>
              </Alert>
           )}
        </div>
      </div>

      {!isEditing && project && (
      <Card className="mb-8 dark:bg-gray-800 shadow-lg">
        <CardHeader className="border-b dark:border-gray-700">
          <div className="flex justify-between items-start">
            <CardTitle className="text-3xl font-bold text-gray-800 dark:text-white">{project.name}</CardTitle>
            {project.is_favorite && <Star className="w-6 h-6 text-yellow-400" />}
          </div>
          {project.description && (
            <CardDescription className="text-gray-600 dark:text-gray-400 pt-2">{project.description}</CardDescription>
          )}
        </CardHeader>
        <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
          <div><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Status</Label><p className="text-gray-800 dark:text-white"><Badge variant={project.status === 'completed' ? 'default' : 'secondary'} className={`${project.status === 'completed' ? 'bg-green-500' : project.status === 'in_progress' ? 'bg-blue-500' : 'bg-gray-500'} text-white`}>{project.status?.replace("_", " ") || "N/A"}</Badge></p></div>
          <div><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Priority</Label><p className="text-gray-800 dark:text-white flex items-center"><Flag className="w-4 h-4 mr-2 text-red-500" /> {project.priority || "N/A"}</p></div>
          <div><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Deadline</Label><p className="text-gray-800 dark:text-white flex items-center"><CalendarDays className="w-4 h-4 mr-2 text-blue-500" /> {formatDate(project.deadline)}</p></div>
          {project.tags && project.tags.length > 0 && (<div className="md:col-span-2"><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Tags</Label><div className="flex flex-wrap gap-2 mt-1">{project.tags.map((tag: string | {name: string}) => (<Badge key={typeof tag === 'string' ? tag : tag.name} variant="outline" className="dark:border-gray-600 dark:text-gray-300"><TagIcon className="w-3 h-3 mr-1" /> {typeof tag === 'string' ? tag : tag.name}</Badge>))}</div></div>)}
        </CardContent>
        <CardFooter className="border-t dark:border-gray-700 pt-4"><p className="text-xs text-gray-500 dark:text-gray-400">Last updated: {formatDate(project.updated_at || project.created_at)}</p></CardFooter>
      </Card>
      )}

      {isEditing && project && ( /* Project Edit Form */ <Card className="my-8 dark:bg-gray-800 shadow-xl"><CardHeader><CardTitle className="text-2xl font-semibold text-gray-800 dark:text-white">Edit Project Details</CardTitle></CardHeader><CardContent>{errorEdit && (<Alert variant="destructive" className="mb-4"><AlertCircleIcon className="h-4 w-4" /><AlertTitle>Update Error</AlertTitle><AlertDescription>{errorEdit}</AlertDescription></Alert>)}<form onSubmit={handleUpdateSubmit} className="space-y-6"><div><Label htmlFor="name-edit" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Project Name <span className="text-red-500">*</span></Label><Input id="name-edit" name="name" type="text" value={editFormData.name || ""} onChange={handleEditChange} required className="dark:bg-gray-700 dark:border-gray-600 dark:text-white" disabled={loadingEdit} /></div><div><Label htmlFor="description-edit" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</Label><Textarea id="description-edit" name="description" value={editFormData.description || ""} onChange={handleEditChange} rows={4} className="dark:bg-gray-700 dark:border-gray-600 dark:text-white" disabled={loadingEdit} /></div><div className="grid grid-cols-1 md:grid-cols-2 gap-6"><div><Label htmlFor="status-edit" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status</Label><Select name="status" value={editFormData.status || "not_started"} onValueChange={(value) => handleEditSelectChange("status", value)} disabled={loadingEdit}><SelectTrigger className="dark:bg-gray-700 dark:border-gray-600 dark:text-white"><SelectValue /></SelectTrigger><SelectContent className="dark:bg-gray-700 dark:text-white"><SelectItem value="not_started">Not Started</SelectItem><SelectItem value="in_progress">In Progress</SelectItem><SelectItem value="on_hold">On Hold</SelectItem><SelectItem value="completed">Completed</SelectItem><SelectItem value="cancelled">Cancelled</SelectItem></SelectContent></Select></div><div><Label htmlFor="priority-edit" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Priority</Label><Select name="priority" value={editFormData.priority?.toString() || "3"} onValueChange={(value) => handleEditSelectChange("priority", parseInt(value))} disabled={loadingEdit}><SelectTrigger className="dark:bg-gray-700 dark:border-gray-600 dark:text-white"><SelectValue /></SelectTrigger><SelectContent className="dark:bg-gray-700 dark:text-white"><SelectItem value="1">Lowest</SelectItem><SelectItem value="2">Low</SelectItem><SelectItem value="3">Medium</SelectItem><SelectItem value="4">High</SelectItem><SelectItem value="5">Highest</SelectItem></SelectContent></Select></div></div><div><Label htmlFor="deadline-edit" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Deadline</Label><Input id="deadline-edit" name="deadline" type="date" value={editFormData.deadline?.toString().split('T')[0] || ""} onChange={handleEditChange} className="dark:bg-gray-700 dark:border-gray-600 dark:text-white" disabled={loadingEdit} /></div><div><Label htmlFor="tags-edit" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tags <span className="text-xs text-gray-500">(comma-separated)</span></Label><Input id="tags-edit" name="tags" type="text" value={Array.isArray(editFormData.tags) ? editFormData.tags.join(", ") : ""} onChange={handleTagChangeEdit} className="dark:bg-gray-700 dark:border-gray-600 dark:text-white" disabled={loadingEdit} /></div><div className="flex justify-end space-x-3 pt-4"><Button type="button" onClick={handleCancelEdit} variant="outline" className="dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700" disabled={loadingEdit}><XCircle className="w-4 h-4 mr-2" /> Cancel</Button><Button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white" disabled={loadingEdit}>{loadingEdit ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="w-4 h-4 mr-2" />} Save Changes</Button></div></form></CardContent></Card>)}

      {/* Summary and AI Context Sections */}
      {!isEditing && project && !project.is_archived && (
        <div className="my-8 grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="dark:bg-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2"><CardTitle className="text-lg font-medium dark:text-white">Project Summary</CardTitle><Button onClick={handleFetchSummary} variant="ghost" size="sm" disabled={loadingSummary} className="dark:text-blue-400 dark:hover:bg-gray-700">{loadingSummary ? <Loader2 className="w-4 h-4 animate-spin" /> : <Info className="w-4 h-4" />}</Button></CardHeader>
            <CardContent>{loadingSummary && <p className="text-sm text-gray-500 dark:text-gray-400">Loading summary...</p>}{projectSummary && !loadingSummary && (<pre className="text-xs bg-gray-100 dark:bg-gray-900 p-3 rounded-md overflow-x-auto text-gray-700 dark:text-gray-300">{JSON.stringify(projectSummary, null, 2)}</pre>)}{!projectSummary && !loadingSummary && <p className="text-sm text-gray-500 dark:text-gray-400">Click to load summary.</p>}</CardContent>
          </Card>

          {/* Enhanced AI Context Section with CRUD */}
          <Card className="dark:bg-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-lg font-medium dark:text-white flex items-center"><Brain className="w-5 h-5 mr-2 text-sky-400"/>AI Contexts</CardTitle>
              <div className="space-x-2">
                <Button onClick={fetchProjectAiContextsList} variant="ghost" size="icon" disabled={loadingAiContextList} className="dark:text-blue-400 dark:hover:bg-gray-700 h-8 w-8"><Brain className="w-4 h-4" /></Button>
                <Button size="sm" onClick={openAiContextFormForNew} className="bg-sky-500 hover:bg-sky-600 text-white text-xs"><PlusSquare className="w-4 h-4 mr-1"/>Create</Button>
              </div>
            </CardHeader>
            <CardContent>
              {loadingAiContextList && <div className="flex justify-center p-2"><Loader2 className="animate-spin w-5 h-5 text-sky-500"/></div>}
              {/* Display error for AI Context list if it occurs specifically */}
              {!loadingAiContextList && aiContexts === null && error && <Alert variant="destructive" className="text-xs"><AlertCircleIcon className="h-3 w-3 mr-1"/><AlertDescription>{error.includes("AI context") ? error: "Could not load AI Contexts."}</AlertDescription></Alert>}
              {aiContexts && !loadingAiContextList && (
                <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                  {aiContexts.length > 0 ? aiContexts.map((ctx) => (
                    <Card key={ctx.id} className="text-xs bg-gray-50 dark:bg-gray-900 p-2.5 rounded-md">
                      <CardContent className="p-0 space-y-1">
                        <div className="flex justify-between items-start mb-1.5">
                            <div><p className="font-medium text-gray-700 dark:text-gray-200">ID: {ctx.id} {ctx.request_id && `(Req: ${ctx.request_id})`}</p></div>
                            <div className="space-x-0.5 flex-shrink-0">
                                <Button variant="ghost" size="icon" className="h-6 w-6 dark:text-gray-400 hover:dark:text-blue-400" onClick={() => openAiContextFormForEdit(ctx)}><Edit3 className="w-3.5 h-3.5"/></Button>
                                <Button variant="ghost" size="icon" className="h-6 w-6 dark:text-gray-400 hover:dark:text-red-400" onClick={() => handleDeleteAiContext(ctx.id)}><Trash2 className="w-3.5 h-3.5"/></Button>
                            </div>
                        </div>
                        <details className="text-gray-600 dark:text-gray-300"><summary className="cursor-pointer text-xs hover:underline">View Data</summary><pre className="mt-1 text-[11px] whitespace-pre-wrap overflow-x-auto bg-gray-100 dark:bg-gray-800 p-1.5 rounded max-h-24">{typeof ctx.context_data === 'string' ? ctx.context_data : JSON.stringify(ctx.context_data, null, 2)}</pre></details>
                        {ctx.notes && <p className="mt-1 pt-1 border-t dark:border-gray-700 text-gray-600 dark:text-gray-300 text-[11px]"><strong>Notes:</strong> {ctx.notes}</p>}
                        <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1">Created: {formatDate(ctx.created_at)} by {ctx.created_by}</p>
                      </CardContent>
                    </Card>
                  )) : <p className="text-sm text-center text-gray-500 dark:text-gray-400 py-3">No AI contexts. Click "Create" to add.</p>}
                </div>
              )}
              {(!aiContexts && !loadingAiContextList && !error) && <p className="text-sm text-gray-500 dark:text-gray-400">Click the <Brain className="inline w-4 h-4"/> icon to load AI contexts.</p>}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Jarvis Chat Section */}
      <Card className="mt-10 dark:bg-gray-800 shadow-lg">
        <CardHeader><CardTitle className="text-2xl font-semibold flex items-center dark:text-white"><MessageSquare className="w-6 h-6 mr-2 text-blue-500" /> Jarvis Chat</CardTitle><CardDescription className="dark:text-gray-400">Chat with Jarvis about this project.</CardDescription></CardHeader>
        <CardContent>
          {loadingChat && <div className="flex justify-center p-4"><Loader2 className="animate-spin w-6 h-6 text-blue-500"/></div>}
          {errorChat && <Alert variant="destructive"><AlertCircleIcon className="h-4 w-4"/><AlertDescription>{errorChat}</AlertDescription></Alert>}
          <div className="h-96 overflow-y-auto p-4 space-y-4 border dark:border-gray-700 rounded-md mb-4 bg-gray-50 dark:bg-gray-900/50">
            {chatMessages.length === 0 && !loadingChat && <p className="text-sm text-center text-gray-500 dark:text-gray-400">No messages yet. Start the conversation!</p>}
            {chatMessages.map((msg, index) => (<div key={msg.id || index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg shadow ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200'}`}><p className="text-sm">{msg.content}</p><p className={`text-xs mt-1 ${msg.role === 'user' ? 'text-blue-200' : 'text-gray-500 dark:text-gray-400'}`}>{formatDate(msg.created_at)}</p></div></div>))}
          </div>
          <form onSubmit={handleSendMessage} className="flex gap-2">
            <Input type="text" value={newMessage} onChange={(e) => setNewMessage(e.target.value)} placeholder="Type your message to Jarvis..." disabled={loadingSendMessage || loadingChat} className="flex-grow dark:bg-gray-700 dark:border-gray-600"/>
            <Button type="submit" disabled={loadingSendMessage || !newMessage.trim()} className="bg-blue-500 hover:bg-blue-600 text-white">{loadingSendMessage ? <Loader2 className="animate-spin w-4 h-4" /> : <Send className="w-4 h-4" />}</Button>
          </form>
        </CardContent>
        <CardFooter className="border-t dark:border-gray-700 pt-4">{chatMessages.length > 0 && (<Button variant="outline" size="sm" onClick={handleDeleteChatHistory} className="text-red-600 border-red-500 hover:bg-red-50 dark:text-red-400 dark:border-red-600 dark:hover:bg-red-900/50"><Trash2 className="w-4 h-4 mr-2"/> Delete Chat History</Button>)}</CardFooter>
      </Card>

      {/* AI Context Form Dialog/Modal */}
      <Dialog open={isAiContextFormOpen} onOpenChange={setIsAiContextFormOpen}>
        <DialogContent className="dark:bg-gray-800 sm:max-w-lg">
          <DialogHeader><DialogTitle className="dark:text-white">{editingAiContext ? "Edit AI Context" : "Create New AI Context"}</DialogTitle><DialogDescription className="dark:text-gray-400">{editingAiContext ? "Modify the details of this AI context." : "Provide data and notes for a new AI context related to this project."}</DialogDescription></DialogHeader>
          {errorAiContextForm && <Alert variant="destructive" className="my-2"><AlertCircleIcon className="h-4 w-4"/><AlertDescription>{errorAiContextForm}</AlertDescription></Alert>}
          <form onSubmit={handleAiContextFormSubmit} className="space-y-4 pt-2">
            <div><Label htmlFor="ai-ctx-data" className="dark:text-gray-300">Context Data (JSON) <span className="text-red-500">*</span></Label><Textarea id="ai-ctx-data" name="context_data" value={(aiContextFormData as any).context_data || ""} onChange={handleAiContextFormChange} rows={7} placeholder='Enter valid JSON...' required className="font-mono text-xs dark:bg-gray-700 dark:border-gray-600" disabled={loadingAiContextForm} /></div>
            <div><Label htmlFor="ai-ctx-notes" className="dark:text-gray-300">Notes</Label><Input id="ai-ctx-notes" name="notes" value={aiContextFormData.notes || ""} onChange={handleAiContextFormChange} placeholder="Optional notes" className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingAiContextForm} /></div>
            {!editingAiContext && (<div><Label htmlFor="ai-ctx-reqid" className="dark:text-gray-300">Request ID</Label><Input id="ai-ctx-reqid" name="request_id" value={aiContextFormData.request_id || ""} onChange={handleAiContextFormChange} placeholder="Optional request ID" className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingAiContextForm} /></div>)}
            <DialogFooter className="pt-3"><DialogClose asChild><Button type="button" variant="outline" className="dark:text-gray-300 dark:border-gray-600" disabled={loadingAiContextForm}>Cancel</Button></DialogClose><Button type="submit" className="bg-green-500 hover:bg-green-600 text-white" disabled={loadingAiContextForm}>{loadingAiContextForm ? <Loader2 className="mr-2 h-4 w-4 animate-spin"/> : <Save className="w-4 h-4 mr-2" />}{editingAiContext ? "Save Changes" : "Create Context"}</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
