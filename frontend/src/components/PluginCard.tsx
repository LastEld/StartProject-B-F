//app/components/PluginCard.tsx
"use client";

import Link from "next/link";
import {
  Card, CardContent, CardFooter, CardHeader, CardTitle
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ArchiveRestore, Zap, PowerOff, Tag, ShieldCheck
} from "lucide-react";
import type { PluginRead } from "@/app/lib/types"; // Точный путь и тип

type PluginCardProps = {
  plugin: PluginRead;
  onAction: (action: "restore" | "activate" | "deactivate", pluginId: number) => Promise<void>;
  isAdmin: boolean;
  className?: string;
};

export default function PluginCard({ plugin, onAction, isAdmin, className }: PluginCardProps) {
  const {
    id,
    name,
    description,
    version,
    is_active,
    is_deleted,
    tags,
    subscription_level,
  } = plugin;

  return (
    <Card className={`w-full flex flex-col justify-between rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 dark:bg-gray-800 dark:border-gray-700 ${className}`}>
      <Link href={`/plugins/${id}`} legacyBehavior>
        <a className="flex-grow block hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-150 rounded-t-lg p-5">
          <CardHeader className="p-0 pb-3">
            <div className="flex justify-between items-start">
              <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                {name || "Unnamed Plugin"}
              </CardTitle>
              <Badge className={`${is_active ? "bg-green-500" : "bg-gray-500"} text-white text-xs`}>
                {is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            {version && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Version: {version}</p>}
          </CardHeader>
          <CardContent className="p-0 space-y-2">
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
                {description}
              </p>
            )}
            <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1 pt-1">
              {subscription_level && (
                <div className="flex items-center">
                  <ShieldCheck className="w-3.5 h-3.5 mr-1.5 text-blue-500" />
                  Subscription: {subscription_level}
                </div>
              )}
            </div>
          </CardContent>
        </a>
      </Link>
      <CardFooter className="border-t dark:border-gray-700 pt-3 pb-3 px-5">
        <div className="flex flex-wrap justify-between items-center w-full gap-2">
          <div className="flex flex-wrap gap-1.5">
            {(tags && Array.isArray(tags)) && tags.slice(0, 3).map((tag: string | { name: string }) => (
              <Badge key={typeof tag === "string" ? tag : tag.name} variant="secondary" className="text-xs px-2 py-0.5">
                <Tag className="w-3 h-3 mr-1" />
                {typeof tag === "string" ? tag : tag.name}
              </Badge>
            ))}
            {(tags && Array.isArray(tags) && tags.length > 3) && (
              <Badge variant="outline" className="text-xs px-2 py-0.5 dark:border-gray-600 dark:text-gray-300">
                +{tags.length - 3} more
              </Badge>
            )}
          </div>
          {isAdmin && (
            <div className="flex gap-2">
              {is_deleted ? (
                <Button
                  variant="outline" size="sm"
                  onClick={e => { e.stopPropagation(); onAction("restore", id); }}
                  className="text-green-600 border-green-500 hover:bg-green-50 dark:text-green-400 dark:border-green-400 dark:hover:bg-green-900/50"
                >
                  <ArchiveRestore className="w-3.5 h-3.5 mr-1.5" /> Restore
                </Button>
              ) : is_active ? (
                <Button
                  variant="outline" size="sm"
                  onClick={e => { e.stopPropagation(); onAction("deactivate", id); }}
                  className="text-red-600 border-red-500 hover:bg-red-50 dark:text-red-400 dark:border-red-400 dark:hover:bg-red-900/50"
                >
                  <PowerOff className="w-3.5 h-3.5 mr-1.5" /> Deactivate
                </Button>
              ) : (
                <Button
                  variant="outline" size="sm"
                  onClick={e => { e.stopPropagation(); onAction("activate", id); }}
                  className="text-green-600 border-green-500 hover:bg-green-50 dark:text-green-400 dark:border-green-400 dark:hover:bg-green-900/50"
                >
                  <Zap className="w-3.5 h-3.5 mr-1.5" /> Activate
                </Button>
              )}
            </div>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}
