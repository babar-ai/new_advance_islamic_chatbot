interface TypingIndicatorProps {
  statusMessage?: string;
}

export default function TypingIndicator({ statusMessage }: TypingIndicatorProps) {
  return (
    <div className="flex items-start gap-3 w-full animate-fade-in">
      {/* Mosque Avatar */}
      <div className="w-9 h-9 rounded-full bg-[#084C3E] dark:bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-2xs mt-0.5">
        <svg viewBox="0 0 48 48" className="w-5 h-5" fill="currentColor">
          <path d="M24 3a3.5 3.5 0 011.5 6.7 3.5 3.5 0 00-.5-6.7z" />
          <path
            d="M24 10c-5.5 4.5-9 10-9 16.5v13.5a1 1 0 001 1h16a1 1 0 001-1V26.5c0-6.5-3.5-12-9-16.5zm-5 27v-8a5 5 0 0110 0v8h-10z"
            fillRule="evenodd"
          />
        </svg>
      </div>

      {/* Typing Bubble */}
      <div className="bg-white dark:bg-[#0F172A] border border-slate-200/90 dark:border-slate-800 rounded-2xl px-5 py-4 shadow-2xs transition-colors">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-[#084C3E] dark:bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.32s]" />
            <span className="w-2 h-2 bg-[#084C3E] dark:bg-emerald-400 rounded-full animate-bounce [animation-delay:-0.16s]" />
            <span className="w-2 h-2 bg-[#084C3E] dark:bg-emerald-400 rounded-full animate-bounce" />
          </div>
          <span className="text-xs text-slate-400 dark:text-slate-500 ml-2 font-medium">
            {statusMessage || "Consulting authentic Islamic sources..."}
          </span>
        </div>
      </div>
    </div>
  );
}

