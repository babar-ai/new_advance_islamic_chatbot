"use client";

import { useState, useRef, FormEvent, useEffect } from "react";

interface InputBarProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export default function InputBar({ onSend, disabled }: InputBarProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea up to 140px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);

  function handleSubmit(e?: FormEvent) {
    if (e) e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;

    onSend(trimmed);
    setInput("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-3 sm:py-4">
      <form
        onSubmit={handleSubmit}
        className="
          flex items-center gap-2 sm:gap-3 bg-white dark:bg-[#0F172A]
          border border-slate-200/90 dark:border-slate-800
          rounded-2xl sm:rounded-full px-4 py-2 sm:py-2.5 shadow-sm hover:shadow-md
          focus-within:border-[#084C3E]/50 dark:focus-within:border-emerald-500/50
          focus-within:ring-1 focus-within:ring-[#084C3E]/20 dark:focus-within:ring-emerald-500/20
          transition-all duration-200
        "
      >
        {/* Attachment / Paperclip Icon */}
        <button
          type="button"
          className="p-1.5 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0 cursor-pointer"
          title="Attach topic or reference"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.8}
              d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
            />
          </svg>
        </button>

        {/* Input Textarea */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask your question about Islam..."
          disabled={disabled}
          rows={1}
          className="
            flex-1 max-h-36 resize-none bg-transparent px-1 py-1.5
            text-sm sm:text-base text-slate-800 dark:text-slate-100
            placeholder-slate-400 dark:placeholder-slate-500
            focus:outline-none disabled:opacity-50 transition-colors
            leading-relaxed
          "
        />

        {/* Send Button */}
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="
            w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-[#084C3E] dark:bg-emerald-600
            hover:bg-[#063B30] dark:hover:bg-emerald-500
            active:bg-[#052F26] text-white flex items-center justify-center
            disabled:opacity-40 disabled:cursor-not-allowed
            shadow-2xs transition-all duration-150 shrink-0 cursor-pointer
          "
          title="Send message"
        >
          <svg className="w-4 h-4 translate-x-px" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
            />
          </svg>
        </button>
      </form>
    </div>
  );
}
