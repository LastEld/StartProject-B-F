"use client";
import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { createAIContext } from "../../lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export default function NewAIContextPage() {
  const router = useRouter();
  const [objectType, setObjectType] = useState("");
  const [objectId, setObjectId] = useState("");
  const [contextData, setContextData] = useState("{}");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data = JSON.parse(contextData || "{}");
      const created = await createAIContext({ object_type: objectType, object_id: Number(objectId), context_data: data });
      router.push(`/ai_context/${created.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create");
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-lg">
      <h1 className="text-2xl font-bold mb-4">New AI Context</h1>
      {error && <div className="text-red-500 mb-2">{error}</div>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input placeholder="object type" value={objectType} onChange={e=>setObjectType(e.target.value)} required />
        <Input placeholder="object id" type="number" value={objectId} onChange={e=>setObjectId(e.target.value)} required />
        <Textarea value={contextData} onChange={e=>setContextData(e.target.value)} rows={6} />
        <Button type="submit">Create</Button>
      </form>
    </div>
  );
}
