"use client";

import { useEffect, useState } from "react";

export default function ApiExplorer() {
  const [routes, setRoutes] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/openapi.json`)
      .then(res => res.json())
      .then(data => setRoutes(Object.entries(data.paths)))
      .catch(e => setError(e.message));
  }, []);

  if (error) return <div>Ошибка: {error}</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl mb-4">Все API эндпоинты (из openapi.json):</h1>
      <ul>
        {routes.map(([path, methods]) => (
          <li key={path} className="mb-2">
            <span className="font-bold">{path}</span>
            <ul className="ml-4">
              {Object.keys(methods as object).map(method => (
                <li key={method} className="inline-block mr-3">
                  <span className="uppercase text-xs bg-gray-200 dark:bg-gray-700 rounded px-2 py-1">{method}</span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}
