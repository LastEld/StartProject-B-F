
// src/app/components/JarvisPanel.tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { listChatMessages, askJarvis } from "../app/lib/api"; // Replaced createChatMessage with askJarvis
import type {
  ChatMessageRead,
  // ChatMessageCreate, // No longer directly used for sending, askJarvis uses JarvisAskRequestType
  AttachmentCreate, // For potential future use with attachments
  JarvisAskRequestType,
  JarvisAskResponseType,
} from "../app/lib/types";
import { Loader2 } from "lucide-react";

export default function JarvisPanel({ projectId }: { projectId: number | undefined }) { // Added projectId prop
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessageRead[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Фетчим историю чата при открытии (опционально)
  useEffect(() => {
    const fetchHistory = async () => {
      if (projectId === undefined) {
        setMessages([{
          id: 0,
          project_id: 0, // No specific project
          role: "jarvis",
          content: "Please select a project to interact with Jarvis.",
          timestamp: new Date().toISOString(),
          metadata: null, author: null, ai_notes: null, attachments: [], is_deleted: false,
        }]);
        return;
      }
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : undefined;
        const chat = await listChatMessages({ project_id: projectId, is_deleted: false }, token || undefined);
        if (chat.length === 0) {
          setMessages([{
            id: 0, // temp id
            project_id: projectId,
            role: "jarvis",
            content: "Hello! I am Jarvis. How can I help you with this project?",
            timestamp: new Date().toISOString(),
            metadata: null, author: null, ai_notes: null, attachments: [], is_deleted: false,
          }]);
        } else {
          setMessages(chat);
        }
      } catch (err) {
        setMessages([
          {
            id: 0, // temp id
            project_id: projectId,
            role: "jarvis",
            content: "Could not load chat history. Please try again later.",
            timestamp: new Date().toISOString(),
            metadata: null, author: null, ai_notes: null, attachments: [], is_deleted: false,
          }
        ]);
      }
    };
    fetchHistory();
  }, [projectId]); // Added projectId to dependency array

  // Автоскролл вниз
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async () => {
    if (!input.trim() || projectId === undefined) return;
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : undefined;

    const userMsgContent = input;
    const tempUserMsgId = Date.now(); // Unique ID for the temporary message

    // Display user's message immediately
    const userMsgForDisplay: ChatMessageRead = {
      id: tempUserMsgId,
      project_id: projectId,
      role: "user",
      content: userMsgContent,
      timestamp: new Date().toISOString(),
      metadata: null, // Ensure all fields of ChatMessageRead are present
      author: null,
      ai_notes: null,
      attachments: [],
      is_deleted: false,
    };
    setMessages((msgs) => [...msgs, userMsgForDisplay]);
    setInput("");
    setLoading(true);

    try {
      const requestData: JarvisAskRequestType = {
        project_id: projectId,
        content: userMsgContent,
        // attachments: [], // TODO: Add attachment handling if UI supports it
      };
      // The askJarvis function is expected to return JarvisAskResponseType
      const response: JarvisAskResponseType = await askJarvis(requestData, token || undefined);

      // Replace temporary user message with confirmed one from backend & add Jarvis's response
      setMessages((prevMessages) => {
        const newMessages = prevMessages.filter(msg => msg.id !== tempUserMsgId); // Remove temp user message
        return [...newMessages, response.user_message, response.jarvis_response]; // Add confirmed messages
      });

    } catch (err: any) {
      let errorMessage = "Jarvis is not available (API error).";
      if (err.message) errorMessage = err.message;
      else if (typeof err.detail === 'string') errorMessage = err.detail;
      else if (Array.isArray(err.detail) && err.detail.length > 0 && err.detail[0].msg) {
        errorMessage = err.detail.map((d: any) => d.msg).join(', ');
      }

      // Display error message from Jarvis
      setMessages((msgs) => [
        ...msgs.filter(msg => msg.id !== tempUserMsgId), // Remove temp user message if error occurs before response
        {
          id: Date.now() + 1, // New ID for error message
          project_id: projectId,
          role: "jarvis", // 'jarvis' or 'system' for error messages
          content: `Error: ${errorMessage}`,
          timestamp: new Date().toISOString(),
          metadata: null, author: "System", ai_notes: null, attachments: [], is_deleted: false,
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
          placeholder={projectId === undefined ? "Select a project to chat" : "Ask Jarvis anything..."}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading || projectId === undefined}
        />
        <button
          type="submit"
          disabled={loading || !input.trim() || projectId === undefined}
          className="px-4 py-2 rounded bg-blue-500 hover:bg-blue-600 text-white font-semibold transition"
        >
          Send
        </button>
      </form>
    </section>
  );
}
