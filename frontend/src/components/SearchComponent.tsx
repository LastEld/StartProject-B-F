//app/components/SearchComponent.tsx
// src/app/components/SearchComponent.tsx
"use client";

import React, { useState, useEffect, ChangeEvent } from "react";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";

type SearchComponentProps = {
  onSearch: (query: string) => void;
  initialQuery?: string;
  placeholder?: string;
  delay?: number; // ms, debounce (по умолчанию 300)
  className?: string;
};

export default function SearchComponent({
  onSearch,
  initialQuery = "",
  placeholder = "Search...",
  delay = 300,
  className = "",
}: SearchComponentProps) {
  const [query, setQuery] = useState(initialQuery);
  const [debounceTimeout, setDebounceTimeout] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Вызываем onSearch с debounce
    if (debounceTimeout) clearTimeout(debounceTimeout);
    const timeout = setTimeout(() => {
      onSearch(query.trim());
    }, delay);
    setDebounceTimeout(timeout);
    // Очищаем таймер при размонтировании
    return () => clearTimeout(timeout);
    // eslint-disable-next-line
  }, [query]);

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Search className="w-5 h-5 text-gray-400" />
      <Input
        type="text"
        value={query}
        onChange={handleChange}
        placeholder={placeholder}
        className="w-full"
      />
    </div>
  );
}
