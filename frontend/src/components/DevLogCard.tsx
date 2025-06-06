//src/app/components/DevLogCard.tsx
// src/app/components/DevLogCard.tsx
"use client";

import Link from "next/link";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ArchiveRestore,
  Tag,
  UserCircle,
  CalendarDays,
  Edit2,
  FileText,
  Zap,
  Users,
  Briefcase,
  CheckCircle
} from "lucide-react";
import type { DevLogRead } from "../app/lib/types"; // Используй types.ts!

type DevLogCardProps = {
  entry: DevLogRead;
  onRestore?: (entryId: number) => Promise<void>;
  className?: string;
};

const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric"
    });
  } catch (e) {
    return "Invalid Date";
  }
};

// Для показа иконки типа записи
const getEntryTypeIcon = (entryType?: string) => {
  switch (entryType?.toLowerCase()) {
    case "meeting":
      return <Users className="w-3 h-3 mr-1.5" />;
    case "code":
      return <Zap className="w-3 h-3 mr-1.5" />;
    case "research":
      return <FileText className="w-3 h-3 mr-1.5" />;
    case "decision":
      return <Edit2 className="w-3 h-3 mr-1.5" />;
    default:
      return <FileText className="w-3 h-3 mr-1.5" />;
  }
};

export default function DevLogCard({ entry, onRestore, className }: DevLogCardProps) {
  const {
    id,
    entry_type,
    content,
    tags,
    author_id,
    created_at,
    is_deleted,
    project_id,
    task_id,
  } = entry;

  // Для удобства: выводим первые 100 символов контента
  const contentSnippet =
    content && content.length > 100
      ? content.substring(0, 100) + "..."
      : content || "No content preview.";

  return (
    <Card className={`w-full flex flex-col justify-between rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 dark:bg-gray-800 dark:border-gray-700 ${className}`}>
      <Link href={`/devlog/${id}`} legacyBehavior>
        <a className="flex-grow block hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-150 rounded-t-lg p-5">
          <CardHeader className="p-0 pb-3">
            <div className="flex justify-between items-start">
              <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
                {entry_type ? entry_type.charAt(0).toUpperCase() + entry_type.slice(1) : "Entry"}
              </CardTitle>
              {/* Здесь можно добавить избранное, если понадобится */}
            </div>
          </CardHeader>
          <CardContent className="p-0 space-y-2">
            <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
              {contentSnippet}
            </p>
            <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
              <div className="flex items-center">
                {getEntryTypeIcon(entry_type)}
                <span>
                  Type:
                  <Badge variant="outline" className="ml-1.5 text-xs dark:border-gray-600 dark:text-gray-300">
                    {entry_type || "N/A"}
                  </Badge>
                </span>
              </div>
              <div className="flex items-center">
                <CalendarDays className="w-3 h-3 mr-1.5 text-blue-500" />
                Date: {formatDate(created_at)}
              </div>
              {author_id && (
                <div className="flex items-center">
                  <UserCircle className="w-3 h-3 mr-1.5 text-green-500" />
                  Author ID: {author_id}
                </div>
              )}
              {project_id && (
                <div className="flex items-center">
                  <Briefcase className="w-3 h-3 mr-1.5 text-indigo-500" />
                  Project ID: {project_id}
                </div>
              )}
              {task_id && (
                <div className="flex items-center">
                  <CheckCircle className="w-3 h-3 mr-1.5 text-teal-500" />
                  Task ID: {task_id}
                </div>
              )}
            </div>
          </CardContent>
        </a>
      </Link>
      <CardFooter className="border-t dark:border-gray-700 pt-3 pb-3 px-5">
        <div className="flex flex-wrap justify-between items-center w-full gap-2">
          <div className="flex flex-wrap gap-1.5">
            {(tags && Array.isArray(tags)) &&
              tags.slice(0, 3).map((tag: string | { name: string }) => (
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
          {is_deleted && onRestore && (
            <Button
              variant="outline"
              size="sm"
              onClick={e => {
                e.stopPropagation();
                onRestore(id);
              }}
              className="text-green-600 border-green-500 hover:bg-green-50 hover:text-green-700 dark:text-green-400 dark:border-green-400 dark:hover:bg-green-900/50 dark:hover:text-green-300 text-xs px-2 py-1 h-auto"
            >
              <ArchiveRestore className="w-3.5 h-3.5 mr-1.5" />
              Restore
            </Button>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}
