// src/app/jarvis/page.tsx
"use client";

import React, { useState } from "react";
import { Send } from "lucide-react";
import JarvisPanel from "../../components/JarvisPanel";

export default function JarvisPage() {
  // Можно сделать отдельное состояние для истории сообщений
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");

  // Пример простой отправки — позже подключим к /api/ask-jarvis
  const sendMessage = async () => {
    if (!input.trim()) return;
    setMessages((prev) => [...prev, { role: "user", content: input }]);
    setInput("");

    // Симуляция ответа (замени на fetch к API!)
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { role: "jarvis", content: "AI is thinking... (подключи backend для реального ответа)" },
      ]);
    }, 600);
  };

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-6 py-8 px-4">
      <h1 className="text-2xl font-bold mb-2 flex items-center gap-2">
        <span>🦾 Jarvis Assistant</span>
      </h1>

      {/* История сообщений */}
      <div className="flex flex-col gap-2 bg-zinc-900 rounded-2xl p-4 min-h-[240px] border border-zinc-800">
        {messages.length === 0 && (
          <span className="text-zinc-400 text-sm">Start a conversation with Jarvis…</span>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={
              msg.role === "user"
                ? "self-end bg-blue-700 text-white rounded-xl px-4 py-2 mb-1"
                : "self-start bg-zinc-800 text-zinc-100 rounded-xl px-4 py-2 mb-1"
            }
          >
            {msg.content}
          </div>
        ))}
      </div>

      {/* Ввод сообщения */}
      <form
        className="flex gap-2"
        onSubmit={e => {
          e.preventDefault();
          sendMessage();
        }}
      >
        <input
          className="flex-1 px-4 py-2 rounded-xl bg-zinc-800 border border-zinc-700 text-white outline-none"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask Jarvis anything about your project…"
        />
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl flex items-center gap-1 transition"
        >
          <Send className="w-4 h-4" />
          Send
        </button>
      </form>

      {/* Можно добавить JarvisPanel как summary/AI analysis */}
      <div className="mt-6">
        <JarvisPanel />
      </div>
    </div>
  );
}
