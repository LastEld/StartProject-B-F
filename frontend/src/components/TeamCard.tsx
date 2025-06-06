//app/components/TeamCard.tsx
// app/components/TeamCard.tsx
"use client";

import Link from "next/link";
import {
  Card, CardContent, CardFooter, CardHeader, CardTitle
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArchiveRestore, Users, UserCircle } from "lucide-react";
import type { TeamRead } from "@/app/lib/types"; // используем строгий импорт

type TeamCardProps = {
  team: TeamRead;
  onRestore?: (teamId: number) => Promise<void>;
  className?: string;
};

export default function TeamCard({
  team, onRestore, className
}: TeamCardProps) {
  const {
    id,
    name,
    description,
    owner_id,
    is_deleted,
    // members, // Добавить, если в API появится массив участников
  } = team;

  return (
    <Card className={`w-full flex flex-col justify-between rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 dark:bg-gray-800 dark:border-gray-700 ${className || ""}`}>
      <Link href={`/teams/${id}`} legacyBehavior>
        <a className="flex-grow block hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-150 rounded-t-lg p-5">
          <CardHeader className="p-0 pb-3">
            <div className="flex justify-between items-start">
              <CardTitle className="text-xl font-semibold text-gray-800 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors flex items-center">
                <Users className="w-5 h-5 mr-2 text-indigo-500 flex-shrink-0" />
                {name || "Unnamed Team"}
              </CardTitle>
              {is_deleted && (
                <Badge variant="outline" className="border-red-500 text-red-500 text-xs">
                  Archived
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-0 space-y-2">
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
                {description}
              </p>
            )}
            <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1 pt-1">
              {owner_id && (
                <div className="flex items-center">
                  <UserCircle className="w-3.5 h-3.5 mr-1.5 text-green-500" />
                  Owner ID: {owner_id}
                </div>
              )}
              {/* 
              // Можно вернуть позже, если добавишь members в TeamRead
              {members && members.length > 0 && (
                <div className="flex items-center">
                  <Users className="w-3.5 h-3.5 mr-1.5 text-blue-500" />
                  {members.length} Member{members.length > 1 ? 's' : ''}
                </div>
              )} 
              */}
            </div>
          </CardContent>
        </a>
      </Link>
      <CardFooter className="border-t dark:border-gray-700 pt-3 pb-3 px-5">
        <div className="flex justify-end items-center w-full gap-2">
          {is_deleted && onRestore && (
            <Button
              variant="outline"
              size="sm"
              onClick={e => { e.stopPropagation(); onRestore(id); }}
              className="text-green-600 border-green-500 hover:bg-green-50 hover:text-green-700 dark:text-green-400 dark:border-green-600 dark:hover:bg-green-700/20"
            >
              <ArchiveRestore className="w-4 h-4 mr-1.5" />
              Restore
            </Button>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}
