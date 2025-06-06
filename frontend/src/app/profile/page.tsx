"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getMe, UserRead, logoutAllSessions } from "../../lib/api"; // Added logoutAllSessions
import { useAuth } from "../../hooks/useAuth"; // Import useAuth for local logout

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Loader2, AlertCircle, UserCircle2, Edit3, CalendarDays, LogOut } from "lucide-react"; // Added LogOut for new button
import Link from "next/link";


// useAuth hook is now imported, no need for local placeholder here

const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try { return new Date(dateString).toLocaleString(undefined, { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
  catch (e) { return "Invalid Date"; }
};

export default function MyProfilePage() {
  const router = useRouter();
  const { user: authUser, token, logout, isLoadingAuth } = useAuth(); // Get logout from useAuth

  const [user, setUser] = useState<UserRead | null>(authUser); // Initialize with user from useAuth
  const [loading, setLoading] = useState(isLoadingAuth); // Sync with useAuth's loading
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchMyProfile = useCallback(async () => {
    if (!token && !isLoadingAuth) { // If no token and auth check is done, redirect
      router.push("/auth/login?redirect=/profile");
      return;
    }
    if (authUser) { // If user is already available from useAuth, use it
        setUser(authUser);
        setLoading(false);
        return;
    }
    // If user not in useAuth but token might exist (e.g. initial load before useAuth resolves)
    if (token) {
        setLoading(true); setError(null);
        try {
          const data = await getMe(token);
          setUser(data);
        } catch (err: any) {
          setError(err.message || "Failed to fetch your profile.");
          setUser(null);
          if (err.message?.includes("401") || err.message?.includes("Not authenticated")) {
            logout(); // Perform full logout if getMe fails due to auth
          }
        }
        finally { setLoading(false); }
    }
  }, [token, router, authUser, isLoadingAuth, logout]);

  useEffect(() => {
    // If useAuth has finished loading and there's no authenticated user, redirect.
    if (!isLoadingAuth && !authUser) {
      router.push("/auth/login?redirect=/profile");
    } else if (authUser) {
      setUser(authUser); // Sync user from useAuth if it changes
      setLoading(false);
    } else if (!isLoadingAuth && token) { // Fallback if authUser not yet populated but token exists
        fetchMyProfile();
    }
  }, [authUser, isLoadingAuth, token, router, fetchMyProfile]);

  const handleLogoutAll = async () => {
    if (!window.confirm("Are you sure you want to log out from all other sessions? Your current session will also be terminated.")) return;
    setActionLoading(true);
    setActionError(null);
    try {
      if (!token) throw new Error("Not authenticated.");
      await logoutAllSessions(token);
      // After successful logout from all sessions, also log out locally.
      await logout();
      // The logout function from useAuth should handle redirection.
    } catch (err: any) {
      setActionError(err.message || "Failed to log out from all sessions.");
    } finally {
      setActionLoading(false);
    }
  };


  if (loading || isLoadingAuth) return <div className="flex justify-center items-center min-h-screen"><Loader2 className="w-12 h-12 animate-spin text-cyan-500" /></div>;
  if (error) return <div className="container mx-auto py-10 px-4"><Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Error</AlertTitle><AlertDescription>{error}</AlertDescription></Alert></div>;
  if (!user) return <div className="container mx-auto py-10 px-4 text-center"><p>Could not load your profile. You might need to log in.</p><Button onClick={() => router.push("/auth/login")} variant="outline" className="mt-4">Go to Login</Button></div>;

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8 max-w-2xl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white flex items-center">
            <UserCircle2 className="w-10 h-10 mr-3 text-cyan-500"/> My Profile
        </h1>
        {user && (
            <Link href={`/users/${user.id}?edit=true`} legacyBehavior>
                <Button variant="outline" className="dark:text-gray-300 dark:border-gray-600">
                    <Edit3 className="w-4 h-4 mr-2" /> Edit Profile
                </Button>
            </Link>
        )}
      </div>

      {actionError && <Alert variant="destructive" className="mb-4"><AlertCircle className="h-4 w-4"/><AlertDescription>{actionError}</AlertDescription></Alert>}

      <Card className="dark:bg-gray-800 shadow-lg">
        <CardHeader className="border-b dark:border-gray-700 pb-4 text-center">
            <UserCircle2 className="w-24 h-24 mx-auto text-cyan-500 mb-3 p-2 bg-cyan-500/10 rounded-full" />
            <CardTitle className="text-3xl font-bold dark:text-white">{user.full_name || user.username}</CardTitle>
            <CardDescription className="dark:text-cyan-400">{user.username} ({user.role || "User"})</CardDescription>
            <Badge variant={user.is_active ? "default" : "destructive"} className={`mt-2 ${user.is_active ? "bg-green-500" : "bg-red-500"}`}>{user.is_active ? "Active Account" : "Account Inactive"}</Badge>
        </CardHeader>
        <CardContent className="pt-6 grid grid-cols-1 gap-y-4">
            <div><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Email Address</Label><p className="dark:text-gray-300 text-base">{user.email}</p></div>
            {user.full_name && <div><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Full Name</Label><p className="dark:text-gray-300 text-base">{user.full_name}</p></div>}
            <div><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">User ID</Label><p className="dark:text-gray-300 text-base">{user.id}</p></div>
            <div><Label className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Current Role</Label><p className="dark:text-gray-300 text-base">{user.role || "user"}</p></div>
        </CardContent>
        <CardFooter className="border-t dark:border-gray-700 pt-4 text-xs text-gray-500 dark:text-gray-400 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center"><CalendarDays className="w-4 h-4 mr-2 text-gray-400"/><span>Joined: {formatDate(user.created_at)}</span></div>
            <div className="flex items-center"><CalendarDays className="w-4 h-4 mr-2 text-gray-400"/><span>Last Login: {formatDate(user.last_login_at)}</span></div>
            <div className="md:col-span-2 pt-2">
                <Button onClick={handleLogoutAll} variant="outline" size="sm" className="w-full dark:text-orange-400 dark:border-orange-600 dark:hover:bg-orange-700/50" disabled={actionLoading}>
                    {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin"/> : <LogOut className="w-4 h-4 mr-2"/>}
                    Logout From All Other Sessions
                </Button>
            </div>
        </CardFooter>
      </Card>
    </div>
  );
}
