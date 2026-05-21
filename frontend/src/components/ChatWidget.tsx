"use client";

/**
 * Floating AI Chat Widget component.
 * Available on all pages. Provides AI-powered cake consultation.
 * Requirements: 3.1, 3.2, 3.7, 3.8, 9.1
 */

import { useState, useRef, useEffect, FormEvent } from "react";
import { useChat, ChatMessage, RecommendationItem } from "@/hooks/useChat";

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const { messages, isLoading, error, isAuthenticated, sendMessage, clearError } =
    useChat();
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    const message = input;
    setInput("");
    await sendMessage(message);
  };

  const formatPrice = (price: number): string => {
    return new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
    }).format(price);
  };

  return (
    <>
      {/* Floating Chat Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-pink-pastel text-white shadow-lg transition-all hover:shadow-xl hover:scale-105 focus:outline-none focus:ring-2 focus:ring-pink-pastel focus:ring-offset-2"
        aria-label={isOpen ? "Đóng chat AI" : "Mở chat AI tư vấn"}
      >
        {isOpen ? (
          <CloseIcon />
        ) : (
          <ChatIcon />
        )}
      </button>

      {/* Chat Panel */}
      {isOpen && (
        <div
          className="fixed z-50 flex flex-col bg-white shadow-2xl
            inset-0 md:inset-auto md:bottom-24 md:right-6 md:h-[600px] md:w-[400px] md:rounded-2xl"
          role="dialog"
          aria-label="AI Chat tư vấn bánh kem"
        >
          {/* Header */}
          <div className="flex items-center justify-between rounded-t-none md:rounded-t-2xl bg-pink-pastel px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="text-lg">🎂</span>
              <h2 className="font-heading text-lg font-semibold text-white">
                AI Tư Vấn
              </h2>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="flex h-8 w-8 items-center justify-center rounded-full text-white/80 hover:bg-white/20 hover:text-white transition-colors"
              aria-label="Đóng chat"
            >
              <CloseIcon />
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {!isAuthenticated ? (
              <LoginPrompt />
            ) : (
              <>
                {messages.map((msg) => (
                  <MessageBubble
                    key={msg.id}
                    message={msg}
                    formatPrice={formatPrice}
                  />
                ))}

                {/* Typing Indicator */}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="rounded-2xl rounded-bl-sm bg-white border border-gray-200 px-4 py-3">
                      <TypingIndicator />
                    </div>
                  </div>
                )}

                {/* Error Message */}
                {error && (
                  <div className="mx-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
                    {error}
                    <button
                      onClick={clearError}
                      className="ml-2 text-red-500 underline hover:text-red-700"
                    >
                      Đóng
                    </button>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input Area */}
          {isAuthenticated && (
            <form
              onSubmit={handleSubmit}
              className="flex items-center gap-2 border-t border-gray-200 px-4 py-3"
            >
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Nhập tin nhắn..."
                disabled={isLoading}
                className="flex-1 rounded-full border border-gray-200 px-4 py-2.5 text-sm text-mocha placeholder-gray-400 focus:border-pink-pastel focus:outline-none focus:ring-1 focus:ring-pink-pastel disabled:opacity-50"
                aria-label="Nhập tin nhắn chat"
                maxLength={2000}
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="flex h-11 w-11 min-w-[44px] items-center justify-center rounded-full bg-pink-pastel text-white transition-colors hover:bg-pink-pastel/90 disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Gửi tin nhắn"
              >
                <SendIcon />
              </button>
            </form>
          )}
        </div>
      )}
    </>
  );
}

// --- Sub-components ---

function MessageBubble({
  message,
  formatPrice,
}: {
  message: ChatMessage;
  formatPrice: (price: number) => string;
}) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "rounded-br-sm bg-pink-pastel/10 text-mocha"
            : "rounded-bl-sm bg-white border border-gray-200 text-mocha"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {/* Product Recommendations */}
        {message.recommendations && message.recommendations.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.recommendations.map((rec, idx) => (
              <RecommendationCard
                key={idx}
                recommendation={rec}
                formatPrice={formatPrice}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function RecommendationCard({
  recommendation,
  formatPrice,
}: {
  recommendation: RecommendationItem;
  formatPrice: (price: number) => string;
}) {
  const productLink = recommendation.product_id
    ? `/products/${recommendation.product_id}`
    : "/products";

  return (
    <div className="rounded-xl border border-gray-100 bg-cream/50 p-3">
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-medium text-mocha text-sm">
          {recommendation.product_name}
        </h4>
        <span className="whitespace-nowrap text-xs font-semibold text-pink-pastel">
          {formatPrice(recommendation.price)}
        </span>
      </div>
      {recommendation.reasoning && (
        <p className="mt-1 text-xs text-gray-600">{recommendation.reasoning}</p>
      )}
      <a
        href={productLink}
        className="mt-2 inline-block text-xs font-medium text-pink-pastel hover:underline"
      >
        Xem chi tiết →
      </a>
    </div>
  );
}

function LoginPrompt() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 py-8 text-center">
      <span className="text-4xl mb-3">🔒</span>
      <p className="text-sm text-mocha font-medium mb-2">
        Đăng nhập để sử dụng AI tư vấn
      </p>
      <p className="text-xs text-gray-500 mb-4">
        Bạn cần đăng nhập để trò chuyện với trợ lý AI của chúng tôi.
      </p>
      <a
        href="/auth/login"
        className="inline-flex h-11 items-center rounded-full bg-pink-pastel px-6 text-sm font-medium text-white hover:bg-pink-pastel/90 transition-colors"
      >
        Đăng nhập
      </a>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1" aria-label="AI đang trả lời">
      <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
      <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
      <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
    </div>
  );
}

// --- Icons ---

function ChatIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="h-6 w-6"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M4.848 2.771A49.144 49.144 0 0112 2.25c2.43 0 4.817.178 7.152.52 1.978.292 3.348 2.024 3.348 3.97v6.02c0 1.946-1.37 3.678-3.348 3.97a48.901 48.901 0 01-3.476.383.39.39 0 00-.297.17l-2.755 4.133a.75.75 0 01-1.248 0l-2.755-4.133a.39.39 0 00-.297-.17 48.9 48.9 0 01-3.476-.384c-1.978-.29-3.348-2.024-3.348-3.97V6.741c0-1.946 1.37-3.68 3.348-3.97z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="h-5 w-5"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M5.47 5.47a.75.75 0 011.06 0L12 10.94l5.47-5.47a.75.75 0 111.06 1.06L13.06 12l5.47 5.47a.75.75 0 11-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 01-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 010-1.06z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="h-5 w-5"
      aria-hidden="true"
    >
      <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
    </svg>
  );
}
