"use client";

import React, { useEffect, useState, ChangeEvent, FormEvent, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getTeam,
  updateTeam,
  deleteTeam, // Soft delete / archive
  restoreTeam,
  hardDeleteTeam, // Permanent delete
  TeamRead,
  TeamUpdate,
} from "../../../lib/api";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Loader2, Edit3, Trash2, Save, XCircle, Info, Users, UserCircle, ArrowLeft, ArchiveRestore, ShieldAlert
} from "lucide-react";

// Placeholder for auth context/hook
const useAuth = () => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    // Replace with actual user object and role/ID from your auth system
    const currentUser = { id: 1, role: "admin" };
    return { currentUser, token, isAdmin: currentUser.role === 'admin' };
};


const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try { return new Date(dateString).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch (e) { return "Invalid Date"; }
};

export default function TeamDetailPage() {
  const router = useRouter();
  const params = useParams();
  const teamIdStr = params.id as string;

  const { currentUser, token, isAdmin } = useAuth();

  const [team, setTeam] = useState<TeamRead | null>(null);
  const isOwner = team?.owner_id === currentUser?.id;
  const canManageTeam = isAdmin || isOwner;

  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState<TeamUpdate>({});

  const [loading, setLoading] = useState(true);
  const [loadingEdit, setLoadingEdit] = useState(false);
  const [loadingAction, setLoadingAction] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [errorEdit, setErrorEdit] = useState<string | null>(null);

  const teamId = parseInt(teamIdStr);

  const fetchTeamDetails = useCallback(async () => {
    if (isNaN(teamId)) { setError("Invalid Team ID."); setLoading(false); return; }
    setLoading(true); setError(null);
    try {
      if (!token) throw new Error("Authentication token not found.");
      const data = await getTeam(teamId, token);
      setTeam(data);
      setEditFormData({ name: data.name, description: data.description });
    } catch (err: any) { setError(err.message || "Failed to fetch team details."); setTeam(null); }
    finally { setLoading(false); }
  }, [teamId, token]);

  useEffect(() => { fetchTeamDetails(); }, [fetchTeamDetails]);

  const handleEditChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setEditFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleUpdateSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!canManageTeam) { setErrorEdit("Unauthorized to edit this team."); return; }
    if (!editFormData.name?.trim()) { setErrorEdit("Team name cannot be empty."); return; }

    setLoadingEdit(true); setErrorEdit(null);
    try {
      if (!token) throw new Error("Authentication token not found.");
      const updated = await updateTeam(teamId, editFormData, token);
      setTeam(updated); setIsEditing(false);
    } catch (err: any) { setErrorEdit(err.message || "Failed to update team."); }
    finally { setLoadingEdit(false); }
  };

  const handleCancelEdit = () => {
    setIsEditing(false); setErrorEdit(null);
    if (team) setEditFormData({ name: team.name, description: team.description });
  };

  const handleTeamAction = async (action: 'archive' | 'restore' | 'hardDelete') => {
    if (!team) return;

    let authorized = false;
    if (action === 'hardDelete') {
        authorized = isAdmin;
    } else { // archive, restore
        authorized = canManageTeam;
    }

    if (!authorized) {
        setError("Unauthorized: You do not have permission for this action.");
        return;
    }

    let confirmMessage = "";
    let apiFunc: Function;

    switch(action) {
        case 'archive': apiFunc = deleteTeam; confirmMessage = "Are you sure you want to archive this team?"; break;
        case 'restore': apiFunc = restoreTeam; confirmMessage = "Are you sure you want to restore this team?"; break;
        case 'hardDelete': apiFunc = hardDeleteTeam; confirmMessage = "Are you sure you want to PERMANENTLY DELETE this team? This action cannot be undone."; break;
        default: return;
    }
    if (!window.confirm(confirmMessage)) return;

    setLoadingAction(true); setError(null);
    try {
      if (!token) throw new Error("Authentication token not found.");
      if (action === 'hardDelete') {
        await apiFunc(teamId, token);
        router.push("/teams");
      } else {
        const result = await apiFunc(teamId, token);
        setTeam(result);
        // fetchTeamDetails(); // Re-fetch for consistency, or rely on returned 'result'
      }
    } catch (err: any) { setError(err.message || `Failed to ${action} team.`); }
    finally { setLoadingAction(false); }
  };

  if (loading) return <div className="flex justify-center items-center min-h-screen"><Loader2 className="w-12 h-12 animate-spin text-indigo-500" /></div>;
  if (error) return <div className="container mx-auto py-10 px-4"><Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Error</AlertTitle><AlertDescription>{error}</AlertDescription><Button onClick={() => router.push("/teams")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" />Back to Teams</Button></Alert></div>;
  if (!team) return <div className="container mx-auto py-10 px-4 text-center"><p>Team not found.</p><Button onClick={() => router.push("/teams")} variant="outline" className="mt-4"><ArrowLeft className="w-4 h-4 mr-2" />Back to Teams</Button></div>;

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex justify-between items-center mb-6">
        <Button onClick={() => router.push("/teams")} variant="outline" size="sm" className="dark:text-gray-300 dark:border-gray-600"><ArrowLeft className="w-4 h-4 mr-2" />Back to Teams</Button>
        {/* Action buttons are now dynamically shown based on canManageTeam and isAdmin */}
        <div className="flex space-x-2">
          {!isEditing && !team.is_deleted && canManageTeam && (<Button onClick={() => setIsEditing(true)} variant="outline" className="dark:text-gray-300 dark:border-gray-600"><Edit3 className="w-4 h-4 mr-2" />Edit</Button>)}
          {!isEditing && team.is_deleted && canManageTeam && (<Button onClick={() => handleTeamAction('restore')} variant="outline" className="text-green-600 border-green-500" disabled={loadingAction}>{loadingAction ? <Loader2 className="w-4 h-4 animate-spin"/> : <ArchiveRestore className="w-4 h-4 mr-2" />}Restore</Button>)}
          {!isEditing && !team.is_deleted && canManageTeam && (<Button onClick={() => handleTeamAction('archive')} variant="destructive" disabled={loadingAction}>{loadingAction ? <Loader2 className="w-4 h-4 animate-spin"/>:<Trash2 className="w-4 h-4 mr-2" />}Archive</Button>)}
          {!isEditing && isAdmin && team.is_deleted && (<Button onClick={() => handleTeamAction('hardDelete')} variant="destructive" className="bg-red-700 hover:bg-red-800" disabled={loadingAction}>{loadingAction ? <Loader2 className="w-4 h-4 animate-spin"/>:<ShieldAlert className="w-4 h-4 mr-2" />}Hard Delete</Button>)}
        </div>
      </div>

      {team.is_deleted && !isEditing && (<Alert variant="default" className="mb-6 bg-yellow-100 border-yellow-400 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-700"><Info className="h-4 w-4" /><AlertTitle>Archived Team</AlertTitle><AlertDescription>This team is archived. {canManageTeam && "You can restore it."} {isAdmin && "Admins can also permanently delete it."}</AlertDescription></Alert>)}

      {!isEditing ? (
        <Card className="mb-8 dark:bg-gray-800 shadow-lg">
          <CardHeader className="border-b dark:border-gray-700 pb-4">
            <div className="flex items-center space-x-3">
                <Users className="w-10 h-10 text-indigo-500"/>
                <div>
                    <CardTitle className="text-3xl font-bold dark:text-white">{team.name}</CardTitle>
                    <CardDescription className="dark:text-gray-400">Team ID: {team.id}</CardDescription>
                </div>
            </div>
          </CardHeader>
          <CardContent className="pt-6 space-y-4">
            <div><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Description</Label><p className="dark:text-gray-300">{team.description || "No description provided."}</p></div>
            <div><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Owner ID</Label><p className="dark:text-gray-300 flex items-center"><UserCircle className="w-4 h-4 mr-1 text-green-500"/>{team.owner_id || "N/A"}</p></div>
            {team.members && team.members.length > 0 && (
                <div><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Members ({team.members.length})</Label>
                <div className="flex flex-wrap gap-2 mt-1">
                    {team.members.map((member: any) => <Badge key={member.id || member} variant="secondary">{member.username || `User ${member.id || member}`}</Badge>)}
                </div></div>
            )}
          </CardContent>
          <CardFooter className="border-t dark:border-gray-700 pt-4 text-xs text-gray-500 dark:text-gray-400">
            <span>Created: {formatDate(team.created_at)}</span><span className="mx-2">|</span><span>Updated: {formatDate(team.updated_at)}</span>
          </CardFooter>
        </Card>
      ) : (
        canManageTeam && <Card className="my-8 dark:bg-gray-800 shadow-xl">
          <CardHeader><CardTitle className="text-2xl font-semibold dark:text-white">Edit Team</CardTitle></CardHeader>
          <CardContent>
            {errorEdit && <Alert variant="destructive" className="mb-4"><AlertCircle className="h-4 w-4" /><AlertTitle>Update Error</AlertTitle><AlertDescription>{errorEdit}</AlertDescription></Alert>}
            <form onSubmit={handleUpdateSubmit} className="space-y-6">
              <div><Label htmlFor="name-edit" className="dark:text-gray-300">Team Name <span className="text-red-500">*</span></Label><Input id="name-edit" name="name" value={editFormData.name || ""} onChange={handleEditChange} required className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
              <div><Label htmlFor="description-edit" className="dark:text-gray-300">Description</Label><Textarea id="description-edit" name="description" value={editFormData.description || ""} onChange={handleEditChange} rows={4} className="dark:bg-gray-700 dark:border-gray-600" disabled={loadingEdit} /></div>
              {/* Owner ID is typically not editable directly by team owner, maybe by superadmin */}
              <div className="flex justify-end space-x-3 pt-4">
                <Button type="button" onClick={handleCancelEdit} variant="outline" className="dark:border-gray-600" disabled={loadingEdit}><XCircle className="w-4 h-4 mr-2" />Cancel</Button>
                <Button type="submit" className="bg-indigo-500 hover:bg-indigo-600 text-white" disabled={loadingEdit}>{loadingEdit ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}Save Changes</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}
      {/* TODO: Section for managing team members if API endpoints exist */}
    </div>
  );
}
