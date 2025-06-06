//app/components/TemplateCard.tsx
// app/components/TemplateCard.tsx
"use client";

import Link from "next/link";
import {
  Card, CardContent, CardFooter, CardHeader, CardTitle
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ArchiveRestore, Tag, UserCircle, CalendarDays, Copy,
  Eye, EyeOff, Zap, PowerOff, Info
} from "lucide-react";
import type { TemplateRead } from "@/app/lib/types";

type TemplateCardProps = {
  template: TemplateRead;
  onRestore?: (templateId: number) => Promise<void>;
  onClone?: (templateId: number) => void;
  className?: string;
};

const formatDate = (dateString?: string | null) => {
  if (!dateString) return "N/A";
  try {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric'
    });
  } catch {
    return "Invalid Date";
  }
};

export default function TemplateCard({
  template, onRestore, onClone, className
}: TemplateCardProps) {
  const {
    id, name, description, tags, author, author_id,
    created_at, is_private, is_active, is_deleted,
    subscription_level
  } = template;

  return (
    <Card className={`w-full flex flex-col justify-between rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 dark:bg-gray-800 dark:border-gray-700 ${className}`}>
      <Link href={`/templates/${id}`} legacyBehavior>
        <a className="flex-grow block hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors duration-150 rounded-t-lg p-5">
          <CardHeader className="p-0 pb-3">
            <div className="flex justify-between items-start">
              <CardTitle className="text-lg font-semibold text-gray-800 dark:text-white hover:text-sky-600 dark:hover:text-sky-400 transition-colors">
                {name || "Untitled Template"}
              </CardTitle>
              <div className="flex items-center space-x-2">
                {is_private
                  ? <Badge variant="outline" className="text-xs border-yellow-500 text-yellow-600 dark:text-yellow-400">
                      <EyeOff className="w-3 h-3 mr-1"/>Private
                    </Badge>
                  : <Badge variant="outline" className="text-xs border-green-500 text-green-600 dark:text-green-400">
                      <Eye className="w-3 h-3 mr-1"/>Public
                    </Badge>
                }
                {is_active
                  ? <Badge className="text-xs bg-green-500 text-white">
                      <Zap className="w-3 h-3 mr-1"/>Active
                    </Badge>
                  : <Badge className="text-xs bg-gray-500 text-white">
                      <PowerOff className="w-3 h-3 mr-1"/>Inactive
                    </Badge>
                }
              </div>
            </div>
            {(author?.full_name || author?.username || author_id) &&
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center">
                <UserCircle className="w-3.5 h-3.5 mr-1.5" />
                {author?.full_name || author?.username || `ID: ${author_id}`}
              </p>
            }
          </CardHeader>
          <CardContent className="p-0 pt-2 space-y-2">
            {description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3 h-[60px]">
                {description}
              </p>
            )}
            <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1 pt-1">
              {subscription_level && (
                <div className="flex items-center">
                  <Info className="w-3.5 h-3.5 mr-1.5 text-blue-500" />
                  Access: {subscription_level}
                </div>
              )}
              <div className="flex items-center">
                <CalendarDays className="w-3.5 h-3.5 mr-1.5 text-gray-500" />
                Created: {formatDate(created_at)}
              </div>
            </div>
          </CardContent>
        </a>
      </Link>
      <CardFooter className="border-t dark:border-gray-700 pt-3 pb-3 px-5">
        <div className="flex flex-wrap justify-between items-center w-full gap-2">
          <div className="flex flex-wrap gap-1.5">
            {tags && tags.slice(0, 3).map((tag: string | { name: string }) => (
              <Badge key={typeof tag === 'string' ? tag : tag.name} variant="secondary" className="text-xs px-2 py-0.5">
                <Tag className="w-3 h-3 mr-1" />
                {typeof tag === 'string' ? tag : tag.name}
              </Badge>
            ))}
            {tags && tags.length > 3 && (
              <Badge variant="outline" className="text-xs px-2 py-0.5 dark:border-gray-600 dark:text-gray-300">
                +{tags.length - 3} more
              </Badge>
            )}
          </div>
          <div className="flex gap-2">
            {is_deleted && onRestore && (
              <Button
                variant="outline" size="sm"
                onClick={e => { e.preventDefault(); e.stopPropagation(); onRestore(id); }}
                className="text-green-600 border-green-500 hover:bg-green-50 hover:text-green-700 dark:text-green-400 dark:border-green-600 dark:hover:bg-green-700/20"
              >
                <ArchiveRestore className="w-3.5 h-3.5 mr-1.5" /> Restore
              </Button>
            )}
            {!is_deleted && onClone && (
              <Button
                variant="default" size="sm"
                onClick={e => { e.preventDefault(); e.stopPropagation(); onClone(id); }}
                className="bg-sky-500 hover:bg-sky-600 text-white"
              >
                <Copy className="w-3.5 h-3.5 mr-1.5" /> Clone
              </Button>
            )}
          </div>
        </div>
      </CardFooter>
    </Card>
  );
}
