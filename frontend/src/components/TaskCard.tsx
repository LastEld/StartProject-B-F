// src/app/components/TaskCard.tsx
// src/app/components/TaskCard.tsx
"use client";

import Link from "next/link";
import {
  Card, CardContent, CardFooter, CardHeader, CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CheckCircle, Circle, User, ArchiveRestore, CalendarDays, Tag, Flag, Briefcase,
} from "lucide-react";
import type { TaskRead, Assignee } from "@/app/lib/types";

type TaskCardProps = {
  task: TaskRead;
  onRestore?: (taskId: number) => Promise<void>;
  className?: string;
};

// Format ISO date string to locale date
const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try {
    return new Date(dateString).toLocaleDateString();
  } catch {
    return "Invalid Date";
  }
};

const getStatusInfo = (status?: string) => {
  switch (status?.toLowerCase()) {
    case "in_progress":
      return { label: "In Progress", icon: <Circle className="w-4 h-4 animate-pulse text-blue-500" />, color: "bg-blue-500 hover:bg-blue-600" };
    case "done":
      return { label: "Done", icon: <CheckCircle className="w-4 h-4 text-green-500" />, color: "bg-green-500 hover:bg-green-600" };
    case "cancelled":
      return { label: "Cancelled", icon: <Circle className="w-4 h-4 text-red-500" />, color: "bg-red-500 hover:bg-red-600"};
    case "backlog":
      return { label: "Backlog", icon: <Circle className="w-4 h-4 text-gray-400" />, color: "bg-gray-400 hover:bg-gray-500"};
    case "todo":
    default:
      return { label: "To Do", icon: <Circle className="w-4 h-4 text-gray-500" />, color: "bg-gray-500 hover:bg-gray-600" };
  }
};

const getPriorityText = (priorityValue?: number) => {
    if (priorityValue === undefined || priorityValue === null) return null;
    if (priorityValue >= 5) return { text: "Highest", color: "text-red-500" };
    if (priorityValue === 4) return { text: "High", color: "text-orange-500" };
    if (priorityValue === 3) return { text: "Medium", color: "text-yellow-500" };
    if (priorityValue === 2) return { text: "Low", color: "text-blue-500" };
    if (priorityValue <= 1) return { text: "Lowest", color: "text-green-500" };
    return { text: priorityValue.toString(), color: "text-gray-500"};
};

// Show first assignee (if present)
const getFirstAssignee = (assignees?: Assignee[] | null) => {
  if (assignees && assignees.length > 0) {
    const a = assignees[0];
    return a.name || a.email || `User ${a.user_id}`;
  }
  return null;
};

export default function TaskCard({ task, onRestore, className }: TaskCardProps) {
  const {
    id,
    title,
    description,
    task_status,
    tags,
    assignees,
    project_id,
    priority,
    deadline,
    is_deleted, // from your types (soft-delete)
    // можно добавить reviewed, ai_notes, etc.
  } = task;

  const statusInfo = getStatusInfo(task_status);
  const priorityInfo = getPriorityText(priority);

  return (
    <Card className={`w-full rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 dark:bg-gray-800 dark:border-gray-700 ${className}`}>
      <Link href={`/tasks/${id}`} legacyBehavior>
        <a className="block hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-150 rounded-t-lg">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white flex items-center">
                {statusInfo.icon}
                <span className="ml-2">{title}</span>
              </CardTitle>
              {priorityInfo && (
                <Badge variant="outline" className={`text-xs ${priorityInfo.color} border-current`}>
                  <Flag className="w-3 h-3 mr-1" /> {priorityInfo.text}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="pt-1 pb-3">
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-3">
                {description}
              </p>
            )}
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
              {deadline && (
                <div className="flex items-center">
                  <CalendarDays className="w-3.5 h-3.5 mr-1.5 text-blue-500" />
                  Deadline: {formatDate(deadline)}
                </div>
              )}
              {project_id && (
                <div className="flex items-center">
                  <Briefcase className="w-3.5 h-3.5 mr-1.5 text-purple-500" />
                  Project ID: {project_id}
                </div>
              )}
              {getFirstAssignee(assignees) && (
                <div className="flex items-center">
                  <User className="w-3.5 h-3.5 mr-1.5 text-green-500" />
                  {getFirstAssignee(assignees)}
                </div>
              )}
            </div>
          </CardContent>
        </a>
      </Link>
      <CardFooter className="border-t dark:border-gray-700 pt-3 pb-3">
        <div className="flex flex-wrap justify-between items-center w-full gap-2">
          <div className="flex flex-wrap gap-1.5">
            <Badge className={`${statusInfo.color} text-white text-xs px-2 py-0.5`}>
              {statusInfo.label}
            </Badge>
            {tags && tags.slice(0, 3).map((tag: string | { name: string }) => (
              <Badge key={typeof tag === "string" ? tag : tag.name} variant="secondary" className="text-xs px-2 py-0.5">
                <Tag className="w-3 h-3 mr-1" />
                {typeof tag === "string" ? tag : tag.name}
              </Badge>
            ))}
            {tags && tags.length > 3 && (
              <Badge variant="outline" className="text-xs px-2 py-0.5">
                +{tags.length - 3} more
              </Badge>
            )}
          </div>
          {is_deleted && onRestore && (
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
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
