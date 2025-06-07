"use client";
import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getAIContext, deleteAIContext } from "../../lib/api";
import { Button } from "@/components/ui/button";

export default function AIContextDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [ctx, setCtx] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAIContext(Number(id))
      .then(setCtx)
      .catch((e:any)=> setError(e.message || "Failed"));
  }, [id]);

  const handleDelete = async () => {
    if(!ctx) return;
    await deleteAIContext(ctx.id).catch(()=>{});
    router.push('/ai_context');
  };

  if(error) return <div className="p-4 text-red-500">{error}</div>;
  if(!ctx) return <div className="p-4">Loading...</div>;

  return (
    <div className="container mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-4">AI Context {ctx.id}</h1>
      <pre className="mb-4 bg-gray-100 p-2 overflow-auto text-sm">{JSON.stringify(ctx, null, 2)}</pre>
      <Button onClick={handleDelete} variant="destructive">Delete</Button>
    </div>
  );
}
