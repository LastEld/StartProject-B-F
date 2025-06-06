
// src/app/components/JarvisPanel.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { createChatMessage, listChatMessages } from "../app/lib/api";
import type { ChatMessageRead, ChatMessageCreate } from "../app/lib/types";
import { Loader2 } from "lucide-react";

export default function JarvisPanel() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessageRead[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Фетчим историю чата при открытии (опционально)
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : undefined;
        const chat = await listChatMessages({ is_deleted: false }, token || undefined);
        setMessages(chat as any); // Или кастни как надо
      } catch (err) {
        setMessages([
          {
            id: 0,
            project_id: 0,
            role: "jarvis",
            content: "Hello! I am Jarvis, your project AI assistant.",
            timestamp: null,
            metadata: null,
            author: null,
            ai_notes: null,
            attachments: [],
            is_deleted: false,
          }
        ]);
      }
    };
    fetchHistory();
  }, []);

  // Автоскролл вниз
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : undefined;

    // Отправляем сообщение пользователя (можно push сразу)
    const userMsg: ChatMessageRead = {
      id: Date.now(), // временный id
      project_id: 0,
      role: "user",
      content: input,
      timestamp: new Date().toISOString(),
      metadata: null,
      author: null,
      ai_notes: null,
      attachments: [],
      is_deleted: false,
    };
    setMessages((msgs) => [...msgs, userMsg]);
    setInput("");
    setLoading(true);

    try {
      // Здесь ждем ответ Jarvis от API
      const req: ChatMessageCreate = {
        project_id: 0, // или id активного проекта, если есть
        role: "user",
        content: userMsg.content,
        attachments: [],
        is_deleted: false,
      };
      const jarvisReply = await createChatMessage(req, token || undefined);
      setMessages((msgs) => [...msgs, jarvisReply]);
    } catch (err: any) {
      setMessages((msgs) => [
        ...msgs,
        {
          ...userMsg,
          id: Date.now() + 1,
          role: "jarvis",
          content: err?.message || "Jarvis is not available (API error).",
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="fixed bottom-0 right-0 w-full sm:w-[360px] bg-zinc-900 border-t sm:border-l border-zinc-800 shadow-2xl rounded-t-xl sm:rounded-tl-xl sm:rounded-tr-none z-40 p-4 flex flex-col gap-2 max-h-[60vh] sm:max-h-[80vh]">
      <h2 className="text-lg font-bold mb-2 text-blue-400">🤖 Jarvis Assistant</h2>
      <div className="flex-1 overflow-y-auto flex flex-col gap-2 mb-2 scrollbar-thin scrollbar-thumb-zinc-700">
        {messages.map((m) => (
          <div
            key={m.id + m.role + (m.timestamp || "")}
            className={`rounded p-2 text-sm ${
              m.role === "user"
                ? "bg-zinc-800 self-end text-right text-blue-300"
                : "bg-zinc-700 self-start text-left text-green-300"
            }`}
          >
            {m.content}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-zinc-400 text-xs italic animate-pulse">
            <Loader2 className="w-4 h-4 animate-spin" />
            Jarvis is typing...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage();
        }}
      >
        <input
          className="flex-1 rounded px-3 py-2 bg-zinc-800 text-white border border-zinc-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
          value={input}
          placeholder="Ask Jarvis anything..."
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-2 rounded bg-blue-500 hover:bg-blue-600 text-white font-semibold transition"
        >
          Send
        </button>
      </form>
    </section>
  );
}
