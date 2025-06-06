//components/NotificationCenter.tsx
"use client";
import React, { useState } from "react";
import { Bell } from "lucide-react";

// Тип уведомления
type Notification = {
  id: string;
  message: string;
  type?: "info" | "success" | "error";
  read?: boolean;
  timestamp?: string;
};

const initialNotifications: Notification[] = [
  { id: "1", message: "Welcome to DevOS Jarvis Web!", type: "info" },
  { id: "2", message: "Project successfully created.", type: "success" },
  { id: "3", message: "Your token will expire soon.", type: "error" },
];

export default function NotificationCenter() {
  const [show, setShow] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>(initialNotifications);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  // В дальнейшем можно расширить до removeNotification, markOneAsRead и интеграции с backend/websocket

  return (
    <div className="relative">
      <button
        className="relative p-2 rounded-full bg-zinc-900 hover:bg-zinc-700 transition"
        onClick={() => setShow((s) => !s)}
        aria-label="Open notifications"
      >
        <Bell className="w-6 h-6 text-white" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-xs px-2 py-0.5 rounded-full text-white">
            {unreadCount}
          </span>
        )}
      </button>
      {show && (
        <div className="absolute right-0 mt-2 w-80 bg-zinc-950 shadow-2xl rounded-2xl border border-zinc-800 z-50 animate-fade-in flex flex-col">
          <div className="flex justify-between items-center px-4 py-2 border-b border-zinc-800">
            <span className="font-bold text-base">Notifications</span>
            <button
              className="text-xs text-blue-400 hover:underline"
              onClick={markAllAsRead}
              disabled={unreadCount === 0}
            >
              Mark all as read
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto flex flex-col">
            {notifications.length === 0 ? (
              <div className="p-4 text-zinc-400 text-sm text-center">
                No notifications
              </div>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  className={`px-4 py-3 border-b border-zinc-800 last:border-0 flex items-start gap-2 ${
                    notif.read ? "opacity-60" : ""
                  }`}
                >
                  <div
                    className={`w-2 h-2 rounded-full mt-2 ${
                      notif.type === "success"
                        ? "bg-green-500"
                        : notif.type === "error"
                        ? "bg-red-500"
                        : "bg-blue-500"
                    }`}
                  />
                  <span>{notif.message}</span>
                  {/* Если нужен timestamp: */}
                  {/* <span className="ml-auto text-xs text-zinc-500">{notif.timestamp}</span> */}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
