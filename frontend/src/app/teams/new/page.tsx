"use client";

import React, { useState, ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createTeam, TeamCreate } from "../../../lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { AlertCircle, Loader2, Users, ArrowLeft } from "lucide-react";

// Placeholder for auth context/hook to get token
const useAuth = () => ({ token: typeof window !== "undefined" ? localStorage.getItem("access_token") : null });


const initialFormData: TeamCreate = {
  name: "",
  description: "",
};

export default function CreateTeamPage() {
  const router = useRouter();
  const { token } = useAuth(); // Use the placeholder hook
  const [formData, setFormData] = useState<TeamCreate>(initialFormData);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError("Team name is required.");
      return;
    }
    setIsLoading(true);
    setError(null);

    try {
      if (!token) throw new Error("Authentication token not found. Please log in.");
      const newTeam = await createTeam(formData, token);

      if (newTeam && newTeam.id) {
        router.push(`/teams/${newTeam.id}`);
      } else {
        // Fallback, though API should ideally return the created object with ID
        router.push("/teams");
      }
    } catch (err: any) {
      setError(err.message || "An unknown error occurred while creating the team.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-xl py-12 px-4">
       <Button onClick={() => router.push("/teams")} variant="outline" size="sm" className="mb-6 dark:text-gray-300 dark:border-gray-600">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Teams List
        </Button>
      <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-10 text-center flex items-center justify-center">
        <Users className="w-8 h-8 mr-3 text-indigo-500" /> Create New Team
      </h1>

      {error && (
        <div className="mb-6 p-4 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-lg flex items-center shadow">
          <AlertCircle className="w-5 h-5 mr-3" /> <p className="text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 p-8 rounded-xl shadow-xl border dark:border-gray-700">
        <div>
          <Label htmlFor="name" className="mb-1 block dark:text-gray-300">Team Name <span className="text-red-500">*</span></Label>
          <Input id="name" name="name" value={formData.name} onChange={handleChange} placeholder="e.g., Marketing Avengers, Core Development" required className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} />
        </div>

        <div>
          <Label htmlFor="description" className="mb-1 block dark:text-gray-300">Description</Label>
          <Textarea id="description" name="description" value={formData.description || ""} onChange={handleChange} rows={4} placeholder="Briefly describe the team's purpose or goals." className="dark:bg-gray-700 dark:border-gray-600" disabled={isLoading} />
        </div>

        {/* Owner ID is usually set by the backend based on the logged-in user creating the team */}

        <div className="pt-4">
          <Button type="submit" className="w-full bg-indigo-500 hover:bg-indigo-600 text-white font-semibold py-3 text-lg rounded-md" disabled={isLoading}>
            {isLoading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <PlusCircle className="mr-2 h-5 w-5" />}
            {isLoading ? "Creating Team..." : "Create Team"}
          </Button>
        </div>
      </form>
    </div>
  );
}
