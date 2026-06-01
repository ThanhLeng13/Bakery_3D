"use client";

/**
 * Custom hook for AI chat state management.
 * Handles session creation, SSE streaming, and message state.
 */

import { useState, useCallback, useRef } from "react";
import { getStoredToken } from "@/lib/auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Types ---
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  recommendations?: RecommendationItem[];
  createdAt: Date;
}

export interface RecommendationItem {
  product_name: string;
  product_id?: string;
  price: number;
  reasoning: string;
}

interface CreateSessionResponse {
  id: string;
  customer_id: string;
  message_count: number;
  created_at: string;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  sendMessage: (content: string) => Promise<void>;
  clearError: () => void;
}

const GREETING_MESSAGE: ChatMessage = {
  id: "greeting",
  role: "assistant",
  content:
    "Xin chào! Tôi là trợ lý AI của tiệm bánh Bơ Nơ. Bạn cần tư vấn bánh cho dịp gì? (sinh nhật, đám cưới, kỷ niệm...)",
  createdAt: new Date(),
};

const ERROR_MESSAGE =
  "Dịch vụ AI tạm thời không khả dụng. Vui lòng thử lại hoặc liên hệ: 0901234567";

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const isAuthenticated = !!getStoredToken();

  const createSession = useCallback(async (): Promise<string> => {
    const token = getStoredToken();
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error("Failed to create chat session");
    }

    const data: CreateSessionResponse = await response.json();
    return data.id;
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      const token = getStoredToken();
      if (!token) {
        setError("Vui lòng đăng nhập để sử dụng chat AI.");
        return;
      }

      setError(null);
      setIsLoading(true);

      // Add user message
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: content.trim(),
        createdAt: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      try {
        // Create session on first message
        if (!sessionIdRef.current) {
          sessionIdRef.current = await createSession();
        }

        // Cancel any previous request
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        const response = await fetch(
          `${API_BASE_URL}/api/v1/chat/sessions/${sessionIdRef.current}/messages?stream=true`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ content: content.trim() }),
            signal: abortControllerRef.current.signal,
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            setError("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
            setIsLoading(false);
            return;
          }
          throw new Error(`HTTP ${response.status}`);
        }

        // Process SSE stream
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let assistantContent = "";
        let recommendations: RecommendationItem[] | undefined;
        const assistantId = `assistant-${Date.now()}`;

        // Add empty assistant message that we'll stream into
        setMessages((prev) => [
          ...prev,
          {
            id: assistantId,
            role: "assistant",
            content: "",
            createdAt: new Date(),
          },
        ]);

        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep the last incomplete line in the buffer
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;

            const dataStr = line.slice(6).trim();
            if (!dataStr || dataStr === "[DONE]") continue;

            try {
              const event = JSON.parse(dataStr);

              if (event.type === "content") {
                assistantContent += event.text;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, content: assistantContent }
                      : msg
                  )
                );
              } else if (event.type === "error") {
                setError(event.message || ERROR_MESSAGE);
                // Remove the empty assistant message
                setMessages((prev) =>
                  prev.filter((msg) => msg.id !== assistantId)
                );
                setIsLoading(false);
                return;
              } else if (event.type === "done") {
                if (event.recommendations && event.recommendations.length > 0) {
                  recommendations = event.recommendations;
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantId
                        ? { ...msg, recommendations }
                        : msg
                    )
                  );
                }
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }

        // If we got no content at all, show error
        if (!assistantContent && !recommendations) {
          setMessages((prev) =>
            prev.filter((msg) => msg.id !== assistantId)
          );
          setError(ERROR_MESSAGE);
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") {
          // Request was cancelled, do nothing
        } else {
          setError(ERROR_MESSAGE);
        }
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, createSession]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    isAuthenticated,
    sendMessage,
    clearError,
  };
}
