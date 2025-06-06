//app/templates/[id]/page.tsx
"use client";

import React, { useEffect, useState, ChangeEvent, FormEvent, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getTemplate,
  updateTemplate,
  deleteTemplate,
  restoreTemplate,
  cloneTemplate,
  TemplateRead,
  TemplateUpdate,
  ProjectCreate,
  ProjectRead,
} from "../..//lib/api";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from "@/components/ui/dialog";
import {
  Loader2, Edit3, Trash2, Save, XCircle, Info, CalendarDays, TagIcon as Tag, UserCircle, ArrowLeft, ArchiveRestore, Copy, LayoutTemplate, ShieldCheck, PowerOff, Zap, Eye, EyeOff
} from "lucide-react";
import ReactMarkdown from 'react-markdown';

const useAuth = () => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const storedUser = typeof window !== "undefined" ? localStorage.getItem("user") : null;
    let currentUser = null;
    let isAdmin = false;
    if (storedUser) {
        try {
            const userObj = JSON.parse(storedUser);
            currentUser = { id: userObj.id, role: userObj.role }; // Assuming id and role are available
            isAdmin = userObj.role === 'admin' || userObj.is_superuser === true;
        } catch (e) { console.error("Failed to parse user from localStorage", e); }
    }
    return { currentUser, token, isAdmin, isAuthenticated: !!token }; // Added isAuthenticated
};

const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try { return new Date(dateString).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch (e) { return "Invalid Date"; }
};

const initialCloneProjectData: ProjectCreate = { name: "", description: "" };

export default function TemplateDetailPage() {
  const router = useRouter();
  const params = useParams();
  const templateIdStr = params.id as string;

  const { currentUser, token, isAdmin, isAuthenticated } = useAuth();

  const [template, setTemplate] = useState<TemplateRead | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState<TemplateUpdate>({});

  const [isCloneModalOpen, setIsCloneModalOpen] = useState(false);
  const [cloneProjectData, setCloneProjectData] = useState<ProjectCreate>(initialCloneProjectData);
  const [loadingClone, setLoadingClone] = useState(false);
  const [errorClone, setErrorClone] = useState<string|null>(null);

  const [loading, setLoading] = useState(true);
  const [loadingEdit, setLoadingEdit] = useState(false);
  const [loadingAction, setLoadingAction] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [errorEdit, setErrorEdit] = useState<string | null>(null);

  const templateId = parseInt(templateIdStr);

  // Derived permission states
  const isAuthor = template?.author_id === currentUser?.id;
  const canManageEntry = isAdmin || isAuthor;
  // Authenticated users can clone public templates. Private templates can only be cloned by author/admin.
  const canCloneTemplate = isAuthenticated && template && (!template.is_private || canManageEntry);

  const fetchTemplateDetails = useCallback(async () => {
    if (isNaN(templateId)) { setError("Invalid Template ID."); setLoading(false); return; }
    setLoading(true); setError(null);
    try {
      if (!token) throw new Error("Authentication token not found for fetching details."); // Should be caught by AuthGuard generally
      const data = await getTemplate(templateId, token);
      setTemplate(data);
      setEditFormData({
        name: data.name,
        description: data.description,
        content: typeof data.content === 'string' ? data.content : JSON.stringify(data.content, null, 2),
        is_active: data.is_active,
        is_private: data.is_private,
        tags: data.tags || [],
        subscription_level_required: data.subscription_level_required,
      });
    } catch (err: any) { setError(err.message || "Failed to fetch template details."); setTemplate(null); }
    finally { setLoading(false); }
  }, [templateId, token]);

  useEffect(() => { fetchTemplateDetails(); }, [fetchTemplateDetails]);

  const handleEditChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setEditFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  const handleEditCheckboxChange = (name: keyof TemplateUpdate, checked: boolean | string) => setEditFormData(prev => ({ ...prev, [name]: Boolean(checked) }));
  const handleEditTagsChange = (e: ChangeEvent<HTMLInputElement>) => setEditFormData(prev => ({ ...prev, tags: e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag) }));
  const handleEditContentChange = (value: string) => setEditFormData(prev => ({ ...prev, content: value }));

  const handleUpdateSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!canManageEntry) { setErrorEdit("Unauthorized: You don't have permission to edit this template."); return; }
    if (!editFormData.name?.trim()) { setErrorEdit("Template name cannot be empty."); return; }

    let parsedContent = editFormData.content;
    try {
        if (typeof editFormData.content === 'string') { parsedContent = JSON.parse(editFormData.content); }
    } catch (jsonError) { setErrorEdit("Content is not valid JSON."); return; }

    setLoadingEdit(true); setErrorEdit(null);
    try {
      if (!token) throw new Error("Authentication token not found.");
      const dataToUpdate: TemplateUpdate = { ...editFormData, content: parsedContent };
      const updated = await updateTemplate(templateId, dataToUpdate, token);
      setTemplate(updated); setIsEditing(false); // fetchTemplateDetails(); // Optionally re-fetch
    } catch (err: any) { setErrorEdit(err.message || "Failed to update template."); }
    finally { setLoadingEdit(false); }
  };

  const handleCancelEdit = () => {
    setIsEditing(false); setErrorEdit(null);
    if (template) setEditFormData({ name: template.name, description: template.description, content: typeof template.content === 'string' ? template.content : JSON.stringify(template.content, null, 2), is_active: template.is_active, is_private: template.is_private, tags: template.tags || [], subscription_level_required: template.subscription_level_required });
  };

  const handleArchiveRestore = async (action: 'archive' | 'restore') => {
    if (!template || !canManageEntry) { setError("Unauthorized or template data missing."); return; }
    let apiFunc = action === 'archive' ? deleteTemplate : restoreTemplate;
    if (!window.confirm(`Are you sure you want to ${action} this template?`)) return;

    setLoadingAction(true); setError(null);
    try {
      if (!token) throw new Error("Authentication token not found.");
      const result = await apiFunc(templateId, token);
      // deleteTemplate returns void, restoreTemplate returns TemplateRead
      setTemplate(action === 'restore' ? result : { ...template, is_deleted: true });
      if (action === 'restore' && result) { fetchTemplateDetails(); } // Ensure full fetch after restore
      else if (action === 'archive') { setTemplate(prev => prev ? {...prev, is_deleted: true} : null); }
    } catch (err: any) { setError(err.message || `Failed to ${action} template.`); }
    finally { setLoadingAction(false); }
  };

  const handleCloneProjectDataChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setCloneProjectData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleCloneSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!canCloneTemplate) { setErrorClone("You do not have permission to clone this template."); return; }
    if (!cloneProjectData.name.trim()) { setErrorClone("New project name is required."); return; }
    setLoadingClone(true); setErrorClone(null);
    try {
        if (!token) throw new Error("Authentication token not found.");
        const newProject = await cloneTemplate(templateId, cloneProjectData, token);
        setIsCloneModalOpen(false);
        router.push(`/projects/${newProject.id}`);
    } catch (err: any) { setErrorClone(err.message || "Failed to clone template."); }
    finally { setLoadingClone(false); }
  };

  if (loading) return <div className="flex justify-center items-center min-h-screen"><Loader2 className="w-12 h-12 animate-spin text-sky-500" /></div>;
  if (error) return <div className="container mx-auto py-10 px-4"><Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Error</AlertTitle><AlertDescription>{error}</AlertDescription><Button onClick={() => router.push("/templates")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" />Back to Templates</Button></Alert></div>;
  if (!template) return <div className="container mx-auto py-10 px-4 text-center"><p>Template not found.</p><Button onClick={() => router.push("/templates")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" />Back to Templates</Button></div>;

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex justify-between items-center mb-6">
        <Button onClick={() => router.push("/templates")} variant="outline" size="sm" className="dark:text-gray-300 dark:border-gray-600"><ArrowLeft className="w-4 h-4 mr-2" />Back to Templates</Button>
        <div className="flex space-x-2">
            {!isEditing && !template.is_deleted && canCloneTemplate && (<Button onClick={() => setIsCloneModalOpen(true)} variant="default" className="bg-sky-500 hover:bg-sky-600 text-white"><Copy className="w-4 h-4 mr-2" />Clone</Button>)}
            {canManageEntry && !isEditing && !template.is_deleted && (<Button onClick={() => setIsEditing(true)} variant="outline" className="dark:text-gray-300 dark:border-gray-600"><Edit3 className="w-4 h-4 mr-2" />Edit</Button>)}
            {canManageEntry && !isEditing && template.is_deleted && (<Button onClick={() => handleArchiveRestore('restore')} variant="outline" className="text-green-600 border-green-500" disabled={loadingAction}>{loadingAction ? <Loader2 className="w-4 h-4 animate-spin"/> : <ArchiveRestore className="w-4 h-4 mr-2" />}Restore</Button>)}
            {canManageEntry && !isEditing && !template.is_deleted && (<Button onClick={() => handleArchiveRestore('archive')} variant="destructive" disabled={loadingAction}>{loadingAction ? <Loader2 className="w-4 h-4 animate-spin"/>:<Trash2 className="w-4 h-4 mr-2" />}Archive</Button>)}
        </div>
      </div>

      {template.is_deleted && !isEditing && (<Alert variant="default" className="mb-6 bg-yellow-100 border-yellow-400 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-700"><Info className="h-4 w-4" /><AlertTitle>Archived Template</AlertTitle><AlertDescription>This template is archived. {canManageEntry && "You can restore it."}</AlertDescription></Alert>)}

      {!isEditing ? (
        <Card className="mb-8 dark:bg-gray-800 shadow-lg">
          <CardHeader className="border-b dark:border-gray-700 pb-4">
            <div className="flex justify-between items-center">
                <CardTitle className="text-3xl font-bold dark:text-white flex items-center"><LayoutTemplate className="w-8 h-8 mr-3 text-sky-500"/>{template.name}</CardTitle>
                <div className="flex items-center space-x-2">
                    {template.is_private ? <Badge variant="outline" className="border-yellow-500 text-yellow-600 dark:text-yellow-400"><EyeOff className="w-3 h-3 mr-1"/>Private</Badge> : <Badge variant="outline" className="border-green-500 text-green-600 dark:text-green-400"><Eye className="w-3 h-3 mr-1"/>Public</Badge>}
                    {template.is_active ? <Badge className="bg-green-500 text-white"><Zap className="w-3 h-3 mr-1"/>Active</Badge> : <Badge className="bg-gray-500 text-white"><PowerOff className="w-3 h-3 mr-1"/>Inactive</Badge>}
                </div>
            </div>
            <CardDescription className="dark:text-gray-400 pt-2">Author ID: {template.author_id || "N/A"} | Created: {formatDate(template.created_at)} | Updated: {formatDate(template.updated_at)}</CardDescription>
            {template.subscription_level_required && <p className="text-xs dark:text-blue-400 flex items-center mt-1"><ShieldCheck className="w-3 h-3 mr-1"/>Requires: {template.subscription_level_required} subscription</p>}
          </CardHeader>
          <CardContent className="pt-6">
            {template.description && <><h3 className="text-lg font-semibold mb-1 dark:text-white">Description</h3><ReactMarkdown className="prose dark:prose-invert max-w-none mb-6">{template.description}</ReactMarkdown></>}
            <h3 className="text-lg font-semibold mb-1 dark:text-white">Content (JSON Structure)</h3>
            <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-4 rounded-md overflow-x-auto dark:text-gray-300">{typeof template.content === 'string' ? template.content : JSON.stringify(template.content, null, 2)}</pre>
          </CardContent>
          <CardFooter className="border-t dark:border-gray-700 pt-4 flex flex-wrap gap-2">
            {template.tags?.map((tag: string | {name:string}) => <Badge key={typeof tag === 'string' ? tag : tag.name} variant="secondary"><Tag className="w-3 h-3 mr-1"/>{typeof tag === 'string' ? tag : tag.name}</Badge>)}
          </CardFooter>
        </Card>
      ) : (
        canManageEntry && <Card className="my-8 dark:bg-gray-800 shadow-xl">
          <CardHeader><CardTitle className="text-2xl font-semibold dark:text-white">Edit Template</CardTitle></CardHeader>
          <CardContent>
            {errorEdit && <Alert variant="destructive" className="mb-4"><AlertCircle className="h-4 w-4" /><AlertTitle>Update Error</AlertTitle><AlertDescription>{errorEdit}</AlertDescription></Alert>}
            <form onSubmit={handleUpdateSubmit} className="space-y-6">
              <div><Label htmlFor="name-edit" className="dark:text-gray-300">Name <span className="text-red-500">*</span></Label><Input id="name-edit" name="name" value={editFormData.name || ""} onChange={handleEditChange} required className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
              <div><Label htmlFor="description-edit" className="dark:text-gray-300">Description</Label><Textarea id="description-edit" name="description" value={editFormData.description || ""} onChange={handleEditChange} rows={3} className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
              <div><Label htmlFor="content-edit" className="dark:text-gray-300">Content (JSON)</Label><Textarea id="content-edit" name="content" value={editFormData.content || ""} onChange={(e) => handleEditContentChange(e.target.value)} rows={10} className="font-mono text-xs dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
              <div className="grid md:grid-cols-2 gap-4">
                <div><Label htmlFor="tags-edit" className="dark:text-gray-300">Tags <span className="text-xs">(comma-separated)</span></Label><Input id="tags-edit" name="tags" value={Array.isArray(editFormData.tags) ? editFormData.tags.join(", ") : ""} onChange={handleEditTagsChange} className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
                <div><Label htmlFor="subscription_level_required-edit" className="dark:text-gray-300">Subscription Level</Label><Input id="subscription_level_required-edit" name="subscription_level_required" value={editFormData.subscription_level_required || ""} onChange={handleEditChange} className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
              </div>
              <div className="flex items-center space-x-4 pt-2">
                  <div className="flex items-center space-x-2"><Checkbox id="is_active-edit" name="is_active" checked={editFormData.is_active || false} onCheckedChange={(checked) => handleEditCheckboxChange("is_active", Boolean(checked))} className="dark:border-gray-600" disabled={loadingEdit}/><Label htmlFor="is_active-edit" className="dark:text-gray-300">Active</Label></div>
                  <div className="flex items-center space-x-2"><Checkbox id="is_private-edit" name="is_private" checked={editFormData.is_private || false} onCheckedChange={(checked) => handleEditCheckboxChange("is_private", Boolean(checked))} className="dark:border-gray-600" disabled={loadingEdit}/><Label htmlFor="is_private-edit" className="dark:text-gray-300">Private</Label></div>
              </div>
              <div className="flex justify-end space-x-3 pt-4">
                <Button type="button" onClick={handleCancelEdit} variant="outline" className="dark:border-gray-600" disabled={loadingEdit}><XCircle className="w-4 h-4 mr-2" />Cancel</Button>
                <Button type="submit" className="bg-sky-500 hover:bg-sky-600 text-white" disabled={loadingEdit}>{loadingEdit ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}Save Changes</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Clone Modal */}
      <Dialog open={isCloneModalOpen} onOpenChange={setIsCloneModalOpen}>
        <DialogContent className="dark:bg-gray-800">
          <DialogHeader><DialogTitle className="dark:text-white">Clone Template to New Project</DialogTitle><DialogDescription className="dark:text-gray-400">Enter details for the new project that will be created from this template.</DialogDescription></DialogHeader>
          {errorClone && <Alert variant="destructive" className="mb-3"><AlertCircle className="h-4 w-4"/><AlertDescription>{errorClone}</AlertDescription></Alert>}
          <form onSubmit={handleCloneSubmit} className="space-y-4 pt-2">
            <div><Label htmlFor="clone-project-name" className="dark:text-gray-300">New Project Name <span className="text-red-500">*</span></Label><Input id="clone-project-name" name="name" value={cloneProjectData.name} onChange={handleCloneProjectDataChange} required className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingClone}/></div>
            <div><Label htmlFor="clone-project-desc" className="dark:text-gray-300">New Project Description</Label><Textarea id="clone-project-desc" name="description" value={cloneProjectData.description || ""} onChange={handleCloneProjectDataChange} rows={3} className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingClone}/></div>
            <DialogFooter className="pt-2">
              <DialogClose asChild><Button type="button" variant="outline" className="dark:text-gray-300 dark:border-gray-600" disabled={loadingClone}>Cancel</Button></DialogClose>
              <Button type="submit" className="bg-sky-500 hover:bg-sky-600 text-white" disabled={loadingClone || !canCloneTemplate}>{loadingClone ? <Loader2 className="mr-2 h-4 w-4 animate-spin"/> : <Copy className="w-4 h-4 mr-2" />}{!canCloneTemplate ? "Permission Denied" : "Clone & Create"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
