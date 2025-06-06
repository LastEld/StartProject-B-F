"use client";

import React, { useEffect, useState, useCallback } from "react";
import { listTeams, TeamRead, TeamFilters, restoreTeam } from "../../lib/api";
import TeamCard from "../../components/TeamCard"; // Using the actual TeamCard
import { PlusCircle, Users, Search, X, ArchiveRestore, Loader2, AlertCircle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
// Badge was part of placeholder, TeamCard will handle its own styling
// import { Badge } from "@/components/ui/badge";


export default function TeamsListPage() {
  const [teams, setTeams] = useState<TeamRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<TeamFilters>({
    include_deleted: false,
  });

  // Placeholder for role check: const { isAdmin } = useAuth();
  const isAdmin = true;

  const fetchTeams = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const teamsData = await listTeams(filters, token ?? undefined);
      setTeams(teamsData);
    } catch (err: any) {
      setTeams([]);
      setError(err.message || "Failed to fetch teams.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchTeams();
  }, [fetchTeams]);

  const handleFilterChange = (key: keyof TeamFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleRestoreTeam = async (teamId: number) => {
    // Placeholder: Add admin/owner check if necessary
    // if (!isAdmin && !isOwnerOfTeam(teamId)) { setError("Unauthorized"); return; }
    const token = localStorage.getItem("access_token");
    if (!token) { setError("Authentication required."); return; }

    try {
      await restoreTeam(teamId, token);
      fetchTeams(); // Refresh list
    } catch (err: any) {
      setError(err.message || `Failed to restore team.`);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
        <h1 className="text-3xl font-bold flex items-center gap-3 text-gray-800 dark:text-white">
          <Users className="w-8 h-8 text-indigo-500" /> Teams
        </h1>
        {/* Link to Create New Team page - consider admin/permission checks here if needed */}
        <Link href="/teams/new" legacyBehavior>
          <Button asChild size="lg" className="bg-indigo-500 hover:bg-indigo-600 text-white">
            <a><PlusCircle className="w-6 h-6 mr-2" /> Create New Team</a>
          </Button>
        </Link>
      </div>

      {/* Filters Section */}
      <div className="mb-8 p-4 md:p-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg border dark:border-gray-700">
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <div className="flex items-center space-x-2">
            <Checkbox
                id="include_deleted-teams"
                checked={filters.include_deleted || false}
                onCheckedChange={(checked) => handleFilterChange("include_deleted", Boolean(checked))}
                className="dark:border-gray-600 data-[state=checked]:bg-indigo-500"
            />
            <Label htmlFor="include_deleted-teams" className="dark:text-gray-300 text-sm font-medium">Show Archived Teams</Label>
          </div>
          {/* Apply button can be added if filters are more complex and shouldn't apply on change */}
          {/* <Button onClick={fetchTeams} className="bg-indigo-500 hover:bg-indigo-600 text-white h-9">
            <Search className="w-4 h-4 mr-2" /> Apply
          </Button> */}
        </div>
      </div>

      {loading && <div className="text-center py-10 dark:text-gray-400"><Loader2 className="w-8 h-8 animate-spin mx-auto text-indigo-500"/>Loading teams...</div>}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" /> <AlertTitle>Error</AlertTitle> <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {!loading && !error && teams.length === 0 && (
        <div className="text-center py-16 text-gray-500 dark:text-gray-400">
          <Users className="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500"/>
          <h2 className="text-xl font-semibold mb-2">No Teams Found</h2>
          <p className="text-sm">
            {filters.include_deleted ? "There are no teams matching your criteria." : "Try showing archived teams or create a new one."}
          </p>
        </div>
      )}
      {!loading && !error && teams.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {teams.map((team) => (
            <TeamCard
                key={team.id}
                team={team}
                onRestore={filters.include_deleted && team.is_deleted ? handleRestoreTeam : undefined}
                // isAdmin={isAdmin} // Pass if needed for card-level actions
            />
          ))}
        </div>
      )}
    </div>
  );
}
