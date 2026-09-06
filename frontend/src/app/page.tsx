"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Message } from "@/lib/types";
import { sendQueryStream, checkBackendHealth } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import InputBar from "@/components/InputBar";
import MessageBubble from "@/components/MessageBubble";
import TypingIndicator from "@/components/TypingIndicator";
import WelcomeScreen from "@/components/WelcomeScreen";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFailedQuery, setLastFailedQuery] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<{ isOnline: boolean; version?: string } | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("chat");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [streamStatus, setStreamStatus] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize theme from localStorage
  useEffect(() => {
    const savedTheme = localStorage.getItem("islamic_knowledge_theme") as "light" | "dark" | null;
    if (savedTheme === "dark") {
      setTheme("dark");
      document.documentElement.classList.add("dark");
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      setTheme("light");
      document.documentElement.classList.remove("dark");
      document.documentElement.setAttribute("data-theme", "light");
    }
  }, []);

  // Theme toggle handler
  const handleToggleTheme = useCallback(() => {
    setTheme((prev) => {
      const nextTheme = prev === "light" ? "dark" : "light";
      try {
        localStorage.setItem("islamic_knowledge_theme", nextTheme);
      } catch {
        // localStorage fallback
      }
      if (nextTheme === "dark") {
        document.documentElement.classList.add("dark");
        document.documentElement.setAttribute("data-theme", "dark");
      } else {
        document.documentElement.classList.remove("dark");
        document.documentElement.setAttribute("data-theme", "light");
      }
      return nextTheme;
    });
  }, []);

  // Check backend health on mount and periodically
  useEffect(() => {
    let isMounted = true;
    async function verifyHealth() {
      const status = await checkBackendHealth();
      if (isMounted) {
        setBackendStatus(status);
      }
    }

    verifyHealth();
    const interval = setInterval(verifyHealth, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Auto-scroll to latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (activeTab === "chat") {
      scrollToBottom();
    }
  }, [messages, isLoading, activeTab]);

  const handleSend = useCallback(
    async (text: string) => {
      if (isLoading || !text.trim()) return;

      setActiveTab("chat");
      setError(null);
      setLastFailedQuery(null);

      // Add user message
      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: text.trim(),
        timestamp: new Date(),
      };

      // Create the assistant message shell immediately (streaming will fill it)
      const botMsgId = crypto.randomUUID();
      const botMsg: Message = {
        id: botMsgId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, botMsg]);
      setIsLoading(true);
      setStreamStatus("Consulting authentic Islamic sources...");

      try {
        await sendQueryStream(
          text.trim(),
          // onToken: append each token to the bot message content
          (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botMsgId
                  ? { ...m, content: m.content + token }
                  : m
              )
            );
          },
          // onStatus: show pipeline phase ("Searching sources..." / "Composing...")
          (_status, message) => {
            setStreamStatus(message);
          }
        );

        // Mark streaming complete
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botMsgId ? { ...m, isStreaming: false } : m
          )
        );
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "An unexpected error occurred while processing your request.";
        setError(errorMessage);
        setLastFailedQuery(text.trim());
        // Remove the empty bot message on error
        setMessages((prev) => prev.filter((m) => m.id !== botMsgId));
      } finally {
        setIsLoading(false);
        setStreamStatus(null);
      }
    },
    [isLoading]
  );

  const handleResetChat = useCallback(() => {
    setMessages([]);
    setError(null);
    setLastFailedQuery(null);
    setActiveTab("chat");
  }, []);

  const handleRetry = useCallback(() => {
    if (lastFailedQuery) {
      handleSend(lastFailedQuery);
    }
  }, [lastFailedQuery, handleSend]);

  const handleToggleSave = useCallback((messageId: string) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId ? { ...msg, isSaved: !msg.isSaved } : msg
      )
    );
  }, []);

  const handleFeedback = useCallback((messageId: string, feedback: "like" | "dislike") => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId ? { ...msg, feedback } : msg
      )
    );
  }, []);

  // Filter saved messages for Bookmarks view
  const savedMessages = messages.filter((m) => m.isSaved && m.role === "assistant");
  // User question history
  const questionHistory = messages.filter((m) => m.role === "user");

  return (
    <div
      className={`flex h-screen w-screen overflow-hidden transition-colors duration-200 ${
        theme === "dark" ? "dark bg-[#090D16] text-slate-100" : "bg-[#FBFBF9] text-slate-800"
      }`}
      data-theme={theme}
    >
      {/* 1. Left Navigation Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onNewChat={handleResetChat}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* 2. Main Chat Column */}
      <div className="flex-1 flex flex-col h-full min-w-0 bg-[#FBFBF9] dark:bg-[#090D16] relative transition-colors duration-200">
        {/* Top Header with Working Theme Toggle */}
        <Header
          backendStatus={backendStatus}
          onOpenMobileSidebar={() => setIsSidebarOpen(true)}
          theme={theme}
          onToggleTheme={handleToggleTheme}
        />

        {/* Dynamic Content View based on activeTab */}
        <main className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 flex flex-col">
          {activeTab === "bookmarks" ? (
            /* Bookmarks View */
            <div className="max-w-3xl mx-auto w-full py-4">
              <div className="flex items-center justify-between mb-6 pb-3 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <h2 className="text-xl font-bold text-[#084C3E] dark:text-emerald-400">Saved Bookmarks</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Verses, Hadiths, and answers you have saved</p>
                </div>
                <button
                  onClick={() => setActiveTab("chat")}
                  className="text-xs font-medium text-[#084C3E] dark:text-emerald-400 hover:underline cursor-pointer"
                >
                  ← Back to Chat
                </button>
              </div>

              {savedMessages.length === 0 ? (
                <div className="text-center py-16 text-slate-400 dark:text-slate-500">
                  <div className="text-4xl mb-3">🔖</div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-300">No saved bookmarks yet</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 max-w-sm mx-auto">
                    Click the &ldquo;Save&rdquo; button on any assistant response to keep it here for quick reference.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {savedMessages.map((msg) => (
                    <MessageBubble
                      key={msg.id}
                      message={msg}
                      onToggleSave={handleToggleSave}
                      onFeedback={handleFeedback}
                    />
                  ))}
                </div>
              )}
            </div>
          ) : activeTab === "history" ? (
            /* History View */
            <div className="max-w-3xl mx-auto w-full py-4">
              <div className="flex items-center justify-between mb-6 pb-3 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <h2 className="text-xl font-bold text-[#084C3E] dark:text-emerald-400">Question History</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Your queries from this session</p>
                </div>
                <button
                  onClick={() => setActiveTab("chat")}
                  className="text-xs font-medium text-[#084C3E] dark:text-emerald-400 hover:underline cursor-pointer"
                >
                  ← Back to Chat
                </button>
              </div>

              {questionHistory.length === 0 ? (
                <div className="text-center py-16 text-slate-400 dark:text-slate-500">
                  <div className="text-4xl mb-3">🕒</div>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-300">No recent questions</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">Questions you ask will appear here.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {questionHistory.map((q) => (
                    <div
                      key={q.id}
                      onClick={() => {
                        setActiveTab("chat");
                      }}
                      className="p-3.5 bg-white dark:bg-[#0F172A] border border-slate-200 dark:border-slate-800 rounded-xl hover:border-[#084C3E]/50 dark:hover:border-emerald-500/50 hover:bg-[#EAF4EE]/30 dark:hover:bg-slate-800/50 cursor-pointer transition-all flex items-center justify-between gap-3 shadow-2xs"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-[#084C3E] dark:text-emerald-400 text-sm">💬</span>
                        <span className="text-sm font-medium text-slate-800 dark:text-slate-200">{q.content}</span>
                      </div>
                      <span className="text-[11px] text-slate-400 dark:text-slate-500 shrink-0">
                        {new Date(q.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : activeTab === "topics" ? (
            /* Topics View */
            <div className="max-w-3xl mx-auto w-full py-4">
              <div className="flex items-center justify-between mb-6 pb-3 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <h2 className="text-xl font-bold text-[#084C3E] dark:text-emerald-400">Islamic Knowledge Topics</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Explore foundational subjects and guidance</p>
                </div>
                <button
                  onClick={() => setActiveTab("chat")}
                  className="text-xs font-medium text-[#084C3E] dark:text-emerald-400 hover:underline cursor-pointer"
                >
                  ← Back to Chat
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[
                  {
                    title: "Qur'an & Tafsir",
                    icon: "📖",
                    prompt: "What does the Qur'an say about patience (Sabr)?",
                    desc: "Divine revelation, meanings, themes, and classical interpretations.",
                  },
                  {
                    title: "Hadith & Sunnah",
                    icon: "📜",
                    prompt: "What are the recorded Hadiths about honesty and truthfulness in trade?",
                    desc: "Authentic sayings, actions, and approvals of the Prophet Muhammad ﷺ.",
                  },
                  {
                    title: "Fiqh & Daily Practice",
                    icon: "⚖️",
                    prompt: "What are the essential requirements and virtues of Salah in Islam?",
                    desc: "Practical rulings regarding prayer, fasting, charity, and daily matters.",
                  },
                  {
                    title: "Seerah & History",
                    icon: "🧭",
                    prompt: "Tell me about the character and compassion of the Prophet Muhammad ﷺ.",
                    desc: "The life, character, and companions of the Prophet Muhammad ﷺ.",
                  },
                  {
                    title: "Duas & Adhkar",
                    icon: "🤲",
                    prompt: "What are authentic morning and evening supplications from the Sunnah?",
                    desc: "Remembrance of Allah, daily supplications, and spiritual protection.",
                  },
                  {
                    title: "Aqeedah (Faith)",
                    icon: "✨",
                    prompt: "Explain the Islamic concept of Tawheed and the six articles of faith.",
                    desc: "Core Islamic theological beliefs, monotheism, and articles of faith.",
                  },
                ].map((item) => (
                  <button
                    key={item.title}
                    type="button"
                    onClick={() => handleSend(item.prompt)}
                    className="p-4 bg-white dark:bg-[#0F172A] border border-slate-200 dark:border-slate-800 rounded-2xl text-left hover:border-[#084C3E] dark:hover:border-emerald-500 hover:shadow-sm transition-all cursor-pointer group"
                  >
                    <div className="flex items-center gap-2.5 mb-2">
                      <span className="text-xl">{item.icon}</span>
                      <h3 className="font-bold text-slate-900 dark:text-slate-100 group-hover:text-[#084C3E] dark:group-hover:text-emerald-400 transition-colors text-sm">
                        {item.title}
                      </h3>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{item.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          ) : activeTab === "settings" ? (
            /* Settings View */
            <div className="max-w-2xl mx-auto w-full py-4">
              <div className="flex items-center justify-between mb-6 pb-3 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <h2 className="text-xl font-bold text-[#084C3E] dark:text-emerald-400">Application Settings</h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Configuration and backend connection details</p>
                </div>
                <button
                  onClick={() => setActiveTab("chat")}
                  className="text-xs font-medium text-[#084C3E] dark:text-emerald-400 hover:underline cursor-pointer"
                >
                  ← Back to Chat
                </button>
              </div>

              <div className="bg-white dark:bg-[#0F172A] border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-4 shadow-2xs">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/80">
                  <div>
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">Interface Theme</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">Toggle between Light and Dark mode</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleToggleTheme}
                    className="px-3.5 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-medium hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors cursor-pointer"
                  >
                    Current: {theme === "light" ? "Light" : "Dark"}
                  </button>
                </div>

                <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/80">
                  <div>
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">Backend API Status</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">FastAPI RAG server endpoint</p>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
                      backendStatus?.isOnline
                        ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/40"
                        : "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800/40"
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        backendStatus?.isOnline ? "bg-emerald-500" : "bg-amber-500"
                      }`}
                    />
                    {backendStatus?.isOnline ? `Online (v${backendStatus.version || "1.0"})` : "Offline"}
                  </span>
                </div>

                <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800/80">
                  <div>
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">API Endpoint</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">Configured via NEXT_PUBLIC_API_URL</p>
                  </div>
                  <code className="text-xs bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-md text-[#084C3E] dark:text-emerald-400 font-mono">
                    {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
                  </code>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <div>
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">Clear Current Session</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">Remove all current messages and restart</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleResetChat}
                    className="px-3.5 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-red-50 dark:hover:bg-red-950 hover:text-red-700 dark:hover:text-red-300 text-slate-600 dark:text-slate-400 text-xs font-medium transition-colors cursor-pointer"
                  >
                    Clear Chat
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* Standard Chat View */
            <>
              {messages.length === 0 ? (
                <WelcomeScreen onSelectSuggestion={handleSend} />
              ) : (
                <div className="max-w-4xl mx-auto w-full space-y-6 pb-16">
                  {/* Minimal top status badge */}
                  <div className="flex justify-center select-none pb-2">
                    <span className="text-[11px] text-slate-400 dark:text-slate-500 bg-white/80 dark:bg-slate-900/80 border border-slate-200/70 dark:border-slate-800 px-3 py-1 rounded-full shadow-2xs">
                      Conversation started • Grounded in Qur&apos;an &amp; Hadith
                    </span>
                  </div>

                  {messages.map((msg) => (
                    <MessageBubble
                      key={msg.id}
                      message={msg}
                      onToggleSave={handleToggleSave}
                      onFeedback={handleFeedback}
                    />
                  ))}

                  {/* Show typing indicator only during search/retrieval phase (before tokens arrive) */}
                  {isLoading && streamStatus && !messages.some((m) => m.isStreaming && m.content.length > 0) && (
                    <TypingIndicator statusMessage={streamStatus} />
                  )}

                  {/* Error State with Retry Button */}
                  {error && (
                    <div className="rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 p-4 text-red-800 dark:text-red-300 text-xs sm:text-sm shadow-xs animate-fade-in">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-2.5">
                          <svg className="w-5 h-5 text-red-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <div>
                            <p className="font-semibold text-red-900 dark:text-red-200">Request Encountered an Issue</p>
                            <p className="mt-1 text-red-700 dark:text-red-300/90 leading-relaxed">{error}</p>
                          </div>
                        </div>

                        {lastFailedQuery && (
                          <button
                            onClick={handleRetry}
                            type="button"
                            className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium text-xs transition-colors shrink-0 cursor-pointer flex items-center gap-1.5 shadow-2xs"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            Retry
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              )}
            </>
          )}
        </main>

        {/* Floating Bottom Input Bar */}
        <footer className="shrink-0 bg-transparent">
          <InputBar onSend={handleSend} disabled={isLoading} />
        </footer>
      </div>
    </div>
  );
}
