// components/ProjectCard.tsx
// components/ProjectCard.tsx
"use client";

import Link from "next/link";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Star, ArchiveRestore, CalendarDays, Tag, Flag } from "lucide-react";
import type { ProjectRead, ProjectShort } from "@/app/lib/types";

type ProjectCardProps = {
  project: ProjectShort | ProjectRead;
  onRestore?: (projectId: number) => Promise<void>;
  className?: string;
};

const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try {
    return new Date(dateString).toLocaleDateString();
  } catch (e) {
    return "Invalid Date";
  }
};

const getStatus = (project: ProjectShort | ProjectRead) =>
  "project_status" in project
    ? project.project_status
    : "status" in project
    ? (project as any).status
    : undefined;

const getIsFavorite = (project: ProjectShort | ProjectRead) =>
  "is_favorite" in project ? project.is_favorite : false;

const getTags = (project: ProjectShort | ProjectRead) =>
  "tags" in project ? project.tags : [];

export default function ProjectCard({ project, onRestore, className }: ProjectCardProps) {
  const {
    id,
    name,
    description = "",
    priority,
    deadline,
    // Не все поля есть в ProjectShort!
  } = project as ProjectRead; // Оставляем для совместимости

  const status = getStatus(project);
  const is_favorite = getIsFavorite(project);
  const tags = getTags(project);

  // Можно добавить is_archived и другие поля по аналогии

  const getStatusBadgeClass = (statusValue?: string) => {
    switch (statusValue?.toLowerCase()) {
      case "completed":
        return "bg-green-500 hover:bg-green-600";
      case "in_progress":
        return "bg-blue-500 hover:bg-blue-600";
      case "on_hold":
        return "bg-yellow-500 hover:bg-yellow-600 text-black";
      case "not_started":
        return "bg-gray-500 hover:bg-gray-600";
      case "cancelled":
        return "bg-red-500 hover:bg-red-600";
      default:
        return "bg-gray-400 hover:bg-gray-500";
    }
  };

  const getPriorityText = (priorityValue?: number) => {
    if (priorityValue === undefined || priorityValue === null) return "N/A";
    if (priorityValue >= 5) return "Highest";
    if (priorityValue === 4) return "High";
    if (priorityValue === 3) return "Medium";
    if (priorityValue === 2) return "Low";
    if (priorityValue <= 1) return "Lowest";
    return priorityValue.toString();
  };

  return (
    <Card
      className={`w-full flex flex-col justify-between rounded-lg shadow-lg hover:shadow-xl transition-shadow duration-300 dark:bg-gray-800 dark:border-gray-700 ${className}`}
    >
      <Link href={`/projects/${id}`} legacyBehavior>
        <a className="flex-grow">
          <CardHeader className="pb-3">
            <div className="flex justify-between items-start">
              <CardTitle className="text-xl font-semibold text-gray-800 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                {name}
              </CardTitle>
              {is_favorite && (
                <Star className="w-5 h-5 text-yellow-400 flex-shrink-0" />
              )}
            </div>
          </CardHeader>
          <CardContent className="flex-grow space-y-3 pt-0">
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
                {description}
              </p>
            )}
            <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
              <CalendarDays className="w-4 h-4 mr-2 text-blue-500" />
              Deadline: {formatDate(deadline)}
            </div>
            {priority !== undefined && priority !== null && (
              <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                <Flag className="w-4 h-4 mr-2 text-red-500" />
                Priority: {getPriorityText(priority)}
              </div>
            )}
          </CardContent>
        </a>
      </Link>
      <CardFooter className="pt-4 border-t dark:border-gray-700">
        <div className="flex flex-wrap justify-between items-center w-full gap-2">
          <div className="flex flex-wrap gap-2">
            {status && (
              <Badge className={`${getStatusBadgeClass(status)} text-white text-xs px-2 py-1 rounded-full`}>
                {status.replace("_", " ")}
              </Badge>
            )}
            {tags && tags.slice(0, 3).map((tag: any) => (
              <Badge
                key={typeof tag === "string" ? tag : tag.name}
                variant="secondary"
                className="text-xs px-2 py-1"
              >
                <Tag className="w-3 h-3 mr-1" />
                {typeof tag === "string" ? tag : tag.name}
              </Badge>
            ))}
            {tags && tags.length > 3 && (
              <Badge variant="outline" className="text-xs px-2 py-1">
                +{tags.length - 3} more
              </Badge>
            )}
          </div>
          {/* Archive/Restore можно добавить по флагу */}
          {/* Пример: {project.is_archived && onRestore && ...} */}
        </div>
      </CardFooter>
    </Card>
  );
}
