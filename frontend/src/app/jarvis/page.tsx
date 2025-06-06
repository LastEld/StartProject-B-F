"use client"; // Required for client-side interactivity

import React, { useState, useEffect, FormEvent, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { askJarvis, getJarvisHistory, getLastJarvisMessages } from '@/app/lib/api';
import { JarvisRequest, JarvisResponse, ChatMessageShort, ChatMessageRead } from '@/app/lib/types';

// Define a unified message type for the chat display
interface DisplayMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  isLoading?: boolean; // For assistant's "Thinking..." state on a specific message
}

export default function JarvisChatPage() {
  const [prompt, setPrompt] = useState<string>('');
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false); // Global loading for API calls
  const [error, setError] = useState<string | null>(null);

  // TODO: Replace with dynamic project ID selection or context
  const MOCK_PROJECT_ID = 1; // Example project ID
  const scrollAreaRef = useRef<HTMLDivElement>(null); // Ref for the ScrollArea's viewport


  // Scroll to bottom effect
  useEffect(() => {
    // This targets the viewport element within ShadCN's ScrollArea.
    // It might need adjustment if the internal structure of ScrollArea changes.
    const scrollViewport = scrollAreaRef.current?.querySelector('div[style*="overflow: scroll"]');
    if (scrollViewport) {
      scrollViewport.scrollTop = scrollViewport.scrollHeight;
    }
  }, [messages]);

  // Load initial messages (using getJarvisHistory for potentially more messages)
  useEffect(() => {
    const fetchInitialMessages = async () => {
      if (MOCK_PROJECT_ID === null || MOCK_PROJECT_ID === undefined) return; // Check MOCK_PROJECT_ID validity
      try {
        setIsLoading(true);
        // Using getJarvisHistory to potentially fetch more history if needed, or getLastJarvisMessages for fewer
        const history: ChatMessageRead[] = await getJarvisHistory(MOCK_PROJECT_ID, { limit: 20 });
        const formattedHistory: DisplayMessage[] = history.map((msg, index) => ({
          id: String(msg.id || `hist_${index}`),
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
          timestamp: msg.timestamp || undefined
        }));
        setMessages(formattedHistory);
        setError(null);
      } catch (err: any) {
        const errorDetail = err.error?.message || err.detail?.[0]?.msg || err.message || 'Failed to load chat history.';
        setError(errorDetail);
        console.error("History loading error:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchInitialMessages();
    // Dependency array: MOCK_PROJECT_ID, if it can change and trigger re-fetch.
    // If it's a true constant for this page, it can be omitted, but good practice to include if it *could* change.
  }, [MOCK_PROJECT_ID]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || MOCK_PROJECT_ID === null || MOCK_PROJECT_ID === undefined) return;

    setError(null);

    const userMessage: DisplayMessage = {
      id: Date.now().toString() + '_user',
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString()
    };

    // Add user message and a temporary loading message for assistant
    setMessages(prev => [...prev, userMessage, {id: Date.now().toString() + '_assistant_loading', role: 'assistant', content: '', isLoading: true, timestamp: new Date().toISOString()}]);
    const currentPrompt = prompt;
    setPrompt(''); // Clear input immediately
    setIsLoading(true); // Global loading state for API call itself

    const requestData: JarvisRequest = {
      prompt: currentPrompt, // Use the captured prompt
      project_id: MOCK_PROJECT_ID,
      model: "llama3"
    };

    try {
      const response = await askJarvis(requestData);
      const assistantMessage: DisplayMessage = {
        id: response.created_at + '_assistant_' + Date.now(), // Ensure unique ID
        role: 'assistant',
        content: response.response,
        timestamp: response.created_at || new Date().toISOString()
      };
      // Replace the loading message with the actual response
      setMessages(prev => prev.filter(m => !m.isLoading).concat(assistantMessage));
    } catch (err: any) {
      const errorDetail = err.error?.message || err.detail?.[0]?.msg || err.message || 'Failed to get response from Jarvis.';
      setError(errorDetail);
      console.error("Jarvis API error:", err);
      // Remove the "Thinking..." message on error and re-add user message if desired (or handle differently)
      setMessages(prev => prev.filter(m => !m.isLoading));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-4 max-w-3xl flex flex-col h-[calc(100vh-8rem)]"> {/* Adjusted height */}
      <Card className="flex-grow flex flex-col shadow-lg">
        <CardHeader className="border-b">
          <CardTitle className="text-2xl font-semibold">Jarvis Chat (Project ID: {MOCK_PROJECT_ID ?? 'N/A'})</CardTitle>
        </CardHeader>
        <CardContent className="flex-grow flex flex-col overflow-hidden p-0">
          <ScrollArea className="flex-grow p-4" ref={scrollAreaRef}>
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`mb-4 p-3 rounded-lg flex flex-col text-sm shadow-sm ${
                  msg.role === 'user'
                    ? 'bg-blue-500 text-white self-end ml-10'
                    : 'bg-slate-100 text-slate-900 self-start mr-10 dark:bg-slate-800 dark:text-slate-50'
                } max-w-[85%]`}
                style={{ alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start' }}
              >
                <p className="font-bold capitalize mb-1 text-xs">{msg.role}</p>
                {msg.isLoading ? (
                    <div className="flex items-center space-x-1.5 py-1">
                        <div className="w-2 h-2 bg-current rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                        <div className="w-2 h-2 bg-current rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                        <div className="w-2 h-2 bg-current rounded-full animate-bounce"></div>
                    </div>
                ) : (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
                {msg.timestamp && !msg.isLoading && (
                  <p className={`text-xs mt-1 pt-1 border-t border-opacity-50 ${msg.role === 'user' ? 'text-blue-200 border-blue-300' : 'text-slate-400 dark:text-slate-500 border-slate-300 dark:border-slate-700'}`}>
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </p>
                )}
              </div>
            ))}
          </ScrollArea>

          <div className="p-4 border-t bg-slate-50 dark:bg-slate-900">
            <form onSubmit={handleSubmit} className="flex items-center gap-2">
              <Input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask Jarvis anything..."
                disabled={isLoading}
                className="flex-grow text-base p-3 rounded-lg border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                aria-label="User prompt"
              />
              <Button type="submit" disabled={isLoading || !prompt.trim()} className="px-6 py-3 text-base">
                {isLoading ? 'Thinking...' : 'Send'}
              </Button>
            </form>
            {error && <p className="text-red-500 mt-2 text-center text-sm">{error}</p>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
