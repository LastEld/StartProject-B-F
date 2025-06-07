"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { listAIContexts, AIContextRead } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function AIContextListPage() {
  const [contexts, setContexts] = useState<AIContextRead[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAIContexts()
      .then(setContexts)
      .catch((e:any) => setError(e.message || "Failed to fetch"));
  }, []);

  if (error) return <div className="p-4 text-red-500">{error}</div>;

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">AI Contexts</h1>
        <Link href="/ai_context/new" legacyBehavior>
          <Button asChild><a>New</a></Button>
        </Link>
      </div>
      <div className="space-y-4">
        {contexts.map(ctx => (
          <Card key={ctx.id} className="dark:bg-gray-800">
            <CardHeader>
              <CardTitle>{ctx.object_type} #{ctx.object_id}</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-sm overflow-auto">{JSON.stringify(ctx.context_data, null, 2)}</pre>
              <Link href={`/ai_context/${ctx.id}`} className="text-blue-600 underline text-sm">View</Link>
            </CardContent>
          </Card>
        ))}
        {contexts.length === 0 && <p>No AI contexts yet.</p>}
      </div>
    </div>
  );
}
